import torch
from groundingdino.models import build_model
from groundingdino.util import box_ops
from groundingdino.util.inference import predict
from groundingdino.util.slconfig import SLConfig
from groundingdino.util.utils import clean_state_dict
from huggingface_hub import hf_hub_download

import groundingdino.datasets.transforms as T


class GDinoInferencer:
    def __init__(self, device):
        self.device = device
        ckpt_repo_id = "ShilongLiu/GroundingDINO"
        ckpt_filename = "groundingdino_swinb_cogcoor.pth"
        ckpt_config_filename = "GroundingDINO_SwinB.cfg.py"
        self.groundingdino = load_model_hf(ckpt_repo_id, ckpt_filename, ckpt_config_filename, device=self.device)

    @staticmethod
    def transform_image(image) -> torch.Tensor:
        transform = T.Compose([
            T.RandomResize([800], max_size=1333),
            T.ToTensor(),
            T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])

        image_transformed, _ = transform(image, None)
        return image_transformed

    def predict_dino(self, image_pil, text_prompt, box_threshold=0.3, text_threshold=0.3):
        image_trans = self.transform_image(image_pil)
        box_list = []
        for desc in text_prompt['descriptions']:
            boxes, logits, phrases = predict(model=self.groundingdino,
                                             image=image_trans,
                                             caption=desc,
                                             box_threshold=box_threshold,
                                             text_threshold=text_threshold,
                                             device=self.device)
            indices = logits.argsort(descending=True)[0]
            boxes = boxes[indices]
            W, H = image_pil.size
            boxes = box_ops.box_cxcywh_to_xyxy(boxes) * torch.Tensor([W, H, W, H])
            box_list.append(boxes)
        return box_list


def load_model_hf(repo_id, filename, ckpt_config_filename, device='cpu'):
    cache_config_file = hf_hub_download(repo_id=repo_id, filename=ckpt_config_filename)

    args = SLConfig.fromfile(cache_config_file)
    model = build_model(args)
    args.device = device

    cache_file = hf_hub_download(repo_id=repo_id, filename=filename)
    checkpoint = torch.load(cache_file, map_location='cpu')
    log = model.load_state_dict(clean_state_dict(checkpoint['model']), strict=False)
    print(f"Model loaded from {cache_file} \n => {log}")
    model.eval()
    return model
