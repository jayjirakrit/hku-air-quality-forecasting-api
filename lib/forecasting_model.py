import numpy as np
import pandas as pd
import os
from sklearn.preprocessing import StandardScaler
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from lib.google_cloud import download_blob_to_file

# Define data model
class AirQualityData(BaseModel):
    date: Optional[datetime] = None
    time: Optional[int] = None
    station: Optional[str] = None
    aqi: Optional[int] = None
    pm2_5: float = None
    temp: Optional[float] = None
    wind: Optional[int] = None
    humidity: Optional[int] = None

# Neural Network Components
class ResidualUnit(nn.Module):
    """Single residual unit with two 3x3 conv layers"""
    def __init__(self, in_channels, out_channels):
        super(ResidualUnit, self).__init__()
        self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm2d(out_channels)
        self.relu1 = nn.ReLU(inplace=True)
        self.conv2 = nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm2d(out_channels)
        self.relu2 = nn.ReLU(inplace=True)
        self.skip_connection = None
        if in_channels != out_channels:
            self.skip_connection = nn.Conv2d(in_channels, out_channels, kernel_size=1)

    def forward(self, x):
        identity = x
        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu1(out)
        out = self.conv2(out)
        out = self.bn2(out)
        if self.skip_connection is not None:
            identity = self.skip_connection(identity)
        out = self.relu2(out)
        return out

class CNNEncoder(nn.Module):
    def __init__(self, in_channels: int, hidden_dims=(32, 32), embed_dim=256):
        super().__init__()
        layers = []
        prev_c = in_channels
        for h in hidden_dims:
            layers += [ResidualUnit(prev_c, h)]
            prev_c = h
        self.conv = nn.Sequential(*layers)
        self.fc = nn.Linear(prev_c * 15**2, embed_dim)

    def forward(self, x):
        z = self.conv(x)
        z = z.flatten(1)
        return self.fc(z)

class PM25CNNLSTM(nn.Module):
    def __init__(self, n_stations, in_channels, cnn_embed=256, lstm_hidden=64, pred_len=24, embed_dim=16):
        super().__init__()
        self.station_emb = nn.Embedding(n_stations, embed_dim)
        self.encoder = CNNEncoder(in_channels, embed_dim=cnn_embed)
        self.lstm = nn.LSTM(cnn_embed + embed_dim, lstm_hidden, batch_first=True)
        self.head = nn.Linear(lstm_hidden, pred_len)

    def forward(self, patch_seq, station_idx):
        B, T, C, H, W = patch_seq.shape
        x = patch_seq.view(B * T, C, H, W)
        z = self.encoder(x)
        z = z.view(B, T, -1)
        emb = self.station_emb(station_idx)
        emb = emb.unsqueeze(1).expand(-1, T, -1)
        lstm_in = torch.cat([z, emb], dim=-1)
        _, (h_n, _) = self.lstm(lstm_in)
        out = self.head(h_n[-1])
        return out

# Dataset Class
class MultiStationDataset(Dataset):
    def __init__(self, X, Y, seq_len=48, pred_len=24):
        self.X, self.Y = X, Y
        self.seq_len, self.pred_len = seq_len, pred_len
        self.S = X.shape[2]
        self.T = X.shape[0]
        self.n_samples = (self.T - seq_len - pred_len + 1) * self.S

    def __len__(self):
        return self.n_samples

    def __getitem__(self, idx):
        t = idx // self.S
        s = idx % self.S
        patch_seq = self.X[t : t + self.seq_len, :, s, :, :]
        y = self.Y[t + self.seq_len : t + self.seq_len + self.pred_len, s]
        return patch_seq.astype(np.float32), np.int64(s), y.astype(np.float32)

# Main Forecasting Function
def forecast_pm25(station_names: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    bucket_name = os.getenv("GBS_BUCKET_NAME")
    source_file = os.getenv("GBS_SOURCE_FILE")
    destination_path = os.getenv("IMAGE_DESTINATION_PATH")
    if not os.path.exists(destination_path):
        print(f"File {destination_path} not found locally. Downloading from GCS")
        download_blob_to_file(bucket_name, source_file, destination_path)
    else:
        print(f"File {destination_path} already exists. Skipping download.")
    
    # Load data
    images = np.load(F"./{destination_path}").astype(np.float32)
    features = [
        "so2", "no", "no2", "rsp", "o3", "fsp", "humidity", "max_temp", 
        "min_temp", "pressure", "wind_direction", "wind_speed", "max_wind_speed", 
        "season", "is_weekend"
    ]
    stations = pd.read_csv("./lib/epd_stations_idx.csv").drop(columns=["Longitude", "Latitude"])
    targets = images[:, features.index("fsp"), stations["lat_idx"], stations["lon_idx"]]
    station_cells = stations[["lat_idx", "lon_idx"]].to_numpy()
    
    # Filter stations if specified
    if station_names is not None:
        station_mask = stations['station'].isin(station_names)
        stations = stations[station_mask]
        station_cells = station_cells[station_mask]
        targets = targets[:, station_mask]
    
    patch_size = 15
    C = 15
    S = len(stations)
    
    # Prepare patches
    pad = patch_size // 2
    images_padded = np.pad(images, ((0, 0), (0, 0), (pad, pad), (pad, pad)), mode="edge")
    windows = np.lib.stride_tricks.sliding_window_view(images_padded, window_shape=(patch_size, patch_size), axis=(2, 3))
    i_idx = station_cells[:, 0]
    j_idx = station_cells[:, 1]
    all_patches = windows[:, :, i_idx, j_idx, :, :]
    
    X_all = all_patches
    Y_all = all_patches[:, features.index("fsp"), :, pad, pad]
    
    # Split data
    n = X_all.shape[0]
    train_end = int(0.8 * n)
    val_end = int(0.9 * n)
    X_test = X_all[val_end:]
    Y_test = Y_all[val_end:]
    
    # Scale data
    scaler = StandardScaler()
    flat_train = X_all[:train_end].transpose(0, 2, 1, 3, 4).reshape(-1, C * patch_size * patch_size)
    scaler.fit(flat_train)
    X_test_s = scaler.transform(
        X_test.transpose(0, 2, 1, 3, 4).reshape(-1, C * patch_size * patch_size)
    ).reshape(X_test.shape[0], X_test.shape[2], C, patch_size, patch_size).transpose(0, 2, 1, 3, 4)
    
    # Create test dataset and loader
    test_ds = MultiStationDataset(X_test_s, Y_test)
    test_loader = DataLoader(test_ds, batch_size=64, shuffle=False)
    
    # Load model
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = PM25CNNLSTM(n_stations=S, in_channels=C, cnn_embed=256, lstm_hidden=64, pred_len=24, embed_dim=16).to(device)
    model.load_state_dict(torch.load("./lib/cnn_lstm_patches_res_best_a.pth", map_location=device))
    model.eval()
    
    xb, station_idx, y_true = next(iter(test_loader))
    xb, station_idx, y_true = xb.to(device), station_idx.to(device), y_true.to(device)

    # 2) Prepare input for LSTM: (B, seq_len, features)
    xb_lstm = xb  # originally (B, features, seq_len)

    # 3) Run your LSTM model
    model.eval()
    with torch.no_grad():
        y_pred = model(xb_lstm, station_idx)  # shape: (B, 24)

    # 4) Move to numpy
    y_true = y_true.cpu().numpy()  # (B, 24)
    y_pred = y_pred.cpu().numpy()  # (B, 24)
    hours = range(1, y_true.shape[1] + 1)

    response_data = []
    # 5) For each station, find a sample in this batch and plot
    for s_idx_tensor in range(17): # Iterate through possible station indices (0-16)
        # find index in batch corresponding to station s_idx_tensor
        # Using .item() to get the scalar value from a 0-d array returned by nonzero()
        idxs = (station_idx.cpu().numpy() == s_idx_tensor).nonzero()
        if len(idxs[0]) == 0: # Check if there are any samples for this station in the batch
            continue
        station_name = stations.iloc[[s_idx_tensor]]['station'].item()
        # Get the first index from the batch that corresponds to the current station
        i = idxs[0][0] 
        # Iterate through the 24 predicted hours for the current station
        for hour_idx, pm2_5_value in enumerate(y_pred[i]):
            response_data.append(
                AirQualityData(
                    date=None,
                    time=hours[hour_idx],
                    station=station_name,
                    pm2_5=float(pm2_5_value),
                    aqi=None,
                    temp=None,
                    wind=None,
                    humidity=None
                ).model_dump()
            )
    
    return response_data