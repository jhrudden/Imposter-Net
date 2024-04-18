from matplotlib import pyplot as plt
import numpy as np
import torch
from typing import Tuple

from src.featurizers import SequenceStateFeaturizer


class SequenceStateVisualizer:
    def __init__(self, featurizer: SequenceStateFeaturizer, cmap="Blues"):
        self.featurizer = featurizer
        self.cmap = cmap
    
    def visualize_global_state(self):
        self._visualize_sequence(self.featurizer.spatial, self.featurizer.states)
    
    def visualize_perspectives(self):
        for (perp, *rest) in self.featurizer.generator():
            self._visualize_sequence(perp)

    def _visualize_step(self, spatial: torch.Tensor, sequence_idx: int, ax=None):

        n_channels, n_rows, n_cols = spatial[sequence_idx, ...].shape
        n_agents = self.featurizer.env.n_agents

        assert n_rows == n_cols, "Only supports square grids"

        if ax is None:
            _, ax = plt.subplots(1, n_agents, figsize=(5 * n_agents, 5))

        cells = np.arange(n_rows)
        ticks = cells - 0.5

        imposters = set(self.featurizer.imposter_locations[sequence_idx].tolist())

        for channel_idx in range(n_channels):
            if channel_idx < n_agents:
                is_imposter = channel_idx in imposters
                role = "Imposter" if is_imposter else "Crewmate"
                ax[channel_idx].set_title(f"{role} {channel_idx}")
            else:
                ax[channel_idx].set_title(f"Other {channel_idx}")

            rotated = np.flipud(spatial[sequence_idx, channel_idx].t().numpy())

            ax[channel_idx].imshow(rotated, cmap=self.cmap)
            ax[channel_idx].grid(True)
            ax[channel_idx].set_xticks(ticks, minor=False)
            ax[channel_idx].set_yticks(ticks, minor=False)
            ax[channel_idx].set_xticklabels([], minor=False)
            ax[channel_idx].set_yticklabels([], minor=False)
            ax[channel_idx].tick_params(axis="both", which="both", length=0)

            for y in cells:
                for x in cells:
                    is_colored = spatial[sequence_idx, channel_idx, x, y]
                    ax[channel_idx].text(
                        x,
                        n_rows - y - 1,
                        str((x, y)),
                        va="center",
                        ha="center",
                        fontsize=8,
                        color="white" if is_colored else "black",
                    )

    def _visualize_sequence(self, spatial: torch.Tensor):
        seq_len, n_channels, _, __ = spatial.size()
        n_agents = self.featurizer.env.n_agents

        _, ax = plt.subplots(seq_len, n_channels, figsize=(n_channels * 5, seq_len * 5))

        for seq_idx in range(seq_len):
            # add title to row
            label = "S$_{t" + ("-" + str(seq_idx) if seq_idx > 0 else "") + "}$"
            ax[seq_idx][0].set_ylabel(label, rotation=0, labelpad=40, fontsize=20)
            self._visualize_step(spatial, seq_idx, ax[seq_idx])

        plt.tight_layout()
        plt.show()
