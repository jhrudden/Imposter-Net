from typing import List
import torch
from torch import nn

from src.utils import calculate_cnn_output_dim


ACTIVATION_FN = {
    "relu": nn.ReLU,
    "sigmoid": nn.Sigmoid,
}


class CNNModel(nn.Module):
    def __init__(
        self,
        n_channels: List[int],
        strides: List[int],
        paddings: List[int],
        kernel_sizes: List[int],
    ):
        super(CNNModel, self).__init__()
        self.n_channels = n_channels
        self.strides = strides
        self.paddings = paddings
        self.kernel_sizes = kernel_sizes

        layers = []
        for idx, (channels, stride, kernel_size, padding) in enumerate(
            zip(n_channels[:-1], strides, kernel_sizes, paddings)
        ):
            layers.append(
                nn.Conv2d(
                    in_channels=channels,
                    out_channels=n_channels[idx + 1],
                    stride=stride,
                    kernel_size=kernel_size,
                    padding=padding,
                )
            )
            layers.append(nn.ReLU())

        self.model = nn.Sequential(*layers)

    def forward(self, x):
        return self.model(x)


class RNNModel(nn.Module):
    def __init__(
        self,
        model_class: nn.Module,
        input_dim: int,
        n_layers: int,
        hidden_dim: int,
        dropout: float,
    ):
        super(RNNModel, self).__init__()
        assert isinstance(model_class, (nn.RNN, nn.GRU))
        nn.RNN(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=n_layers,
            dropout=dropout,
            batch_first=True,
        )
        self.model = model_class()

    def forward(self, x):
        return self.model(x)  # (output, hidden state)


class SpacialDQN(nn.Module):

    def __init__(
        self,
        # Feature size args
        input_image_size: int,
        non_spatial_input_size: int,
        # CNN arguments
        n_channels: List[int],
        strides: List[int],
        paddings: List[int],
        kernel_sizes: List[int],
        # RNN arguments
        rnn_model: nn.Module,
        rnn_layers: int,
        rnn_hidden_dim: int,
        rnn_dropout: float,
        # MLP arguments
        mlp_hidden_layer_dims: List[int],
        n_actions: int,
    ):
        super(RNNModel, self).__init__()

        # Making CNN
        self.input_image_size = input_image_size
        self.n_channels = n_channels
        self.strides = strides
        self.paddings = paddings
        self.kernel_sizes = kernel_sizes

        self.cnn = CNNModel(
            n_channels=n_channels,
            strides=strides,
            paddings=paddings,
            kernel_sizes=kernel_sizes,
        )

        # calculating the number of features out of CNN
        self.cnn_ouput_dim = (
            calculate_cnn_output_dim(
                input_size=input_image_size,
                kernel_sizes=kernel_sizes,
                strides=strides,
                paddings=paddings,
            )
            ** 2
        )

        # Making RNN
        self.rnn_model = rnn_model
        self.rnn_layers = rnn_layers
        self.rnn_hidden_dim = rnn_hidden_dim
        self.rnn_dropout = rnn_dropout

        self.rnn = RNNModel(
            model_class=rnn_model,
            input_dim=self.cnn_ouput_dim + non_spatial_input_size,
            n_layers=rnn_layers,
            hidden_dim=rnn_hidden_dim,
            dropout=rnn_dropout,
        )

        # MLP Prediction head
        self.n_actions = n_actions
        self.mlp_dims = [rnn_hidden_dim] + mlp_hidden_layer_dims + [n_actions]
        self.prediction_head = make_mlp(layer_dims=self.mlp_dims, activation_fn="relu")

    def forward(self, spatial_x, non_spatial_x):

        # running through CNN
        batch_size, timesteps, C, H, W = spatial_x.size()
        cnn_in = spatial_x.view(batch_size * timesteps, C, H, W)
        cnn_out = self.cnn(cnn_in)

        # Reshape the output for the RNN
        cnn_out = cnn_out.view(batch_size, timesteps, -1)
        # appending non-spatial features
        rnn_in = torch.cat((cnn_out, non_spatial_x), dim=2)
        rnn_out, _ = self.rnn(rnn_in)

        # Use the last hidden state to predict with MLP
        mlp_in = self.rnn(rnn_out[:, -1, :])
        out = self.prediction_head(mlp_in)

        return out


def make_mlp(layer_dims, activation_fn):
    a = ACTIVATION_FN[activation_fn]

    layers = []

    for idx, dim in enumerate(layer_dims[:-1]):
        layers.append(nn.Linear(in_features=dim, out_features=layer_dims[idx + 1]))
        layers.append(a())

    return nn.Sequential(*layers[:-1])