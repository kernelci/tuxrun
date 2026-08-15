# vim: set ts=4
#
# Copyright 2021-present Linaro Limited
#
# SPDX-License-Identifier: MIT

import yaml

FullLoader = None
for loader in ["CFullLoader", "CLoader", "FullLoader", "Loader"]:
    if hasattr(yaml, loader):
        if loader != "CFullLoader":
            print("Warning: using python yaml loader")
        FullLoader = getattr(yaml, loader)
        break

assert FullLoader is not None


def yaml_load(data):
    return yaml.load(data, Loader=FullLoader)


def yaml_dump(data):
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=1000000)
