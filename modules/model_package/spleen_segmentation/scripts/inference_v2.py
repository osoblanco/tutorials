
# Copyright 2020 - 2021 MONAI Consortium
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import json

import torch
from monai.apps import ConfigParser
from monai.data import decollate_batch
from monai.inferers import Inferer
from monai.transforms import Transform
from monai.utils.enums import CommonKeys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base_config', '-c', type=str, help='file path of base config', required=False)
    parser.add_argument('--config', '-c', type=str, help='config file to override base config', required=True)
    parser.add_argument('--meta', '-e', type=str, help='file path of the meta data')
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    configs = {}

    # load meta data
    with open(args.meta, "r") as f:
        configs.update(json.load(f))
    # load base config file, can override meta data in config
    with open(args.base_config, "r") as f:
        configs.update(json.load(f))
    # load config file, add or override the content of base config
    with open(args.config, "r") as f:
        new_configs = json.load(f)
    # override the inferer with other args
    configs["inferer"] = new_configs["inferer"]
    # override spacing transform with other pixdims
    configs["preprocessing"][1] = new_configs["preprocessing"]

    model: torch.nn.Module = None
    dataloader: torch.utils.data.DataLoader = None
    inferer: Inferer = None
    postprocessing: Transform = None
    # TODO: parse inference config file and construct instances
    config_parser = ConfigParser(configs)
    # instantialize the components immediately
    model = config_parser.get_instance("model").to(device)
    dataloader = config_parser.get_instance("dataloader")
    inferer = config_parser.get_instance("inferer")
    postprocessing = config_parser.get_instance("postprocessing")

    model.eval()
    with torch.no_grad():
        for d in dataloader:
            images = d[CommonKeys.IMAGE].to(device)
            # define sliding window size and batch size for windows inference
            d[CommonKeys.PRED] = inferer(inputs=images, predictor=model)
            # decollate the batch data into a list of dictionaries, then execute postprocessing transforms
            [postprocessing(i) for i in decollate_batch(d)]


if __name__ == '__main__':
    main()
