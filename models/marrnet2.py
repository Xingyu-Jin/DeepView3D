from os import makedirs
from os.path import join
import numpy as np
import torch
import torch.nn as nn
from networks.networks import ImageEncoder, VoxelDecoder
from .marrnetbase import MarrnetBaseModel


class Model(MarrnetBaseModel):
    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument(
            '--canon_sup',
            action='store_true',
            help="Use canonical-pose voxels as supervision"
        )

        # Model to evaluate
        parser.add_argument(
            '--trained_model',
            type=str, default=None,
            help='Path to pretrained model'
        )

        parser.add_argument(
            '--pred_thresh',
            type=float, default=0.5,
            help='Prediction evaluation threshold'
        )
        return parser, set()

    def __init__(self, opt, logger):
        super(Model, self).__init__(opt, logger)
        if opt.canon_sup:
            voxel_key = 'voxel_canon'
        else:
            voxel_key = 'voxel'
        self.voxel_key = voxel_key
        self.requires = ['rgb', 'depth', 'normal', 'silhou', voxel_key]
        self.net = Net(4)

        # For model evaluation
        if opt.trained_model:
            state_dict = torch.load(opt.trained_model)['nets'][0]
#            if 'shapehd' is in opt.trained_model:
#                temp_dict = {}
#                for key in state_dict.keys():
#                    if key.startswith("marrnet2."):
#                        temp_dict[key[9:len(key)]] = state_dict[key]
#                self.net.load_state_dict(temp_dict)
#            else:
#                self.net.load_state_dict(state_dict)
            self.net.load_state_dict(state_dict)

        self.pred_thresh = opt.pred_thresh
        self.criterion = nn.BCEWithLogitsLoss(reduction='elementwise_mean')
        self.optimizer = self.adam(
            self.net.parameters(),
            lr=opt.lr,
            **self.optim_params
        )
        self._nets = [self.net]
        self._optimizers.append(self.optimizer)
        self.input_names = ['depth', 'normal', 'silhou']
        self.gt_names = [voxel_key]
        self.init_vars(add_path=True)
        self._metrics = ['loss']
        self.init_weight(self.net)

    def __str__(self):
        return "MarrNet-2 predicting voxels from 2.5D sketches"

    def _train_on_batch(self, epoch, batch_idx, batch):
        self.net.zero_grad()
        pred = self.predict(batch)
        loss, loss_data = self.compute_loss(pred)
        loss.backward()
        self.optimizer.step()
        batch_size = len(batch['rgb_path'])
        batch_log = {'size': batch_size, **loss_data}
        return batch_log

    def _vali_on_batch(self, epoch, batch_idx, batch):
        pred = self.predict(batch, no_grad=True)
        _, loss_data = self.compute_loss(pred)
        if np.mod(epoch, self.opt.vis_every_vali) == 0:
            if batch_idx < self.opt.vis_batches_vali:
                outdir = join(self.full_logdir, 'epoch%04d_vali' % epoch)
                makedirs(outdir, exist_ok=True)
                output = self.pack_output(pred, batch)
                self.visualizer.visualize(output, batch_idx, outdir)
                np.savez(join(outdir, 'batch%04d' % batch_idx), **output)
        batch_size = len(batch['rgb_path'])
        batch_log = {'size': batch_size, **loss_data}
        return batch_log

    def _vali2_on_batch(self, epoch, batch_idx, batch):
        pred = self.predict(batch, no_grad=True)
        _, loss_data = self.calculate_iou(pred)
        batch_size = len(batch['rgb_path'])
        batch_log = {'size': batch_size, **loss_data}
        return batch_log

    def calculate_iou(self, pred):
        sigm = nn.Sigmoid()
        pred_sigm = sigm(pred)
        iou = self.evaluate_iou(pred_sigm, getattr(self._gt, self.voxel_key), self.pred_thresh)
        iou_data = {}
        iou_data['loss'] = iou.mean().item()
        return iou, iou_data

    def pack_output(self, pred, batch, add_gt=True):
        out = {}
        out['rgb_path'] = batch['rgb_path']
        out['pred_voxel'] = pred.detach().cpu().numpy()
        if add_gt:
            out['gt_voxel'] = batch[self.voxel_key].numpy()
            out['normal_path'] = batch['normal_path']
            out['depth_path'] = batch['depth_path']
            out['silhou_path'] = batch['silhou_path']
        return out

    def compute_loss(self, pred):
        loss = self.criterion(pred, getattr(self._gt, self.voxel_key))
        loss_data = {}
        loss_data['loss'] = loss.mean().item()
        return loss, loss_data


class Net(nn.Module):
    """
    2.5D maps to 3D voxel
    """

    def __init__(self, in_planes, encode_dims=200, silhou_thres=0):
        super().__init__()
        self.encoder = ImageEncoder(in_planes, encode_dims=encode_dims)
        self.decoder = VoxelDecoder(n_dims=encode_dims, nf=512)
        self.silhou_thres = silhou_thres

    def forward(self, input_struct):
        depth = input_struct.depth
        normal = input_struct.normal
        silhou = input_struct.silhou
        # Mask
        is_bg = silhou <= self.silhou_thres
        depth[is_bg] = 0
        normal[is_bg.repeat(1, 3, 1, 1)] = 0 # NOTE: if old net2, set to white (100),
        x = torch.cat((depth, normal), 1) # and swap depth and normal
        # Forward
        latent_vec = self.encoder(x)
        vox = self.decoder(latent_vec)
        return vox
