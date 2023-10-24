"""
Copyright 2023 Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""
import os
from .lambda_runtime_features import feature_list


class FeatureGate:
    def __init__(self, execution_env=os.environ.get("AWS_EXECUTION_ENV")):
        self.__execution_env = execution_env

    def is_feature_enabled(self, feature_name) -> bool:
        if self.__execution_env is None or self.__execution_env in feature_list.get(
            feature_name
        ):
            return True
        else:
            return False


feature_handler = FeatureGate()
