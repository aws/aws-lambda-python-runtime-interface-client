import os
import unittest
from parameterized import parameterized
from awslambdaric.lambda_runtime_features import feature_list
from awslambdaric.lambda_runtime_feature_handler import FeatureGate


feature_names = [(feature_name,) for feature_name in feature_list]
execution_envs = (
    "AWS_Lambda_python3.12",
    "AWS_Lambda_python3.11",
    "AWS_Lambda_python3.10",
    "AWS_Lambda_python3.9",
)
execution_envs_not_enabled_lambda_marshaller_ensure_ascii_false = tuple(
    set(execution_envs).difference(
        feature_list.get("lambda_marshaller_ensure_ascii_false")
    )
)
execution_envs_is_enabled_lambda_marshaller_ensure_ascii_false = tuple(
    feature_list.get("lambda_marshaller_ensure_ascii_false")
)


class TestLambdaRuntimeFeatures(unittest.TestCase):
    @parameterized.expand(feature_names)
    def test_no_execution_env_all_features_enabled(self, feature_name):
        feature_handler = FeatureGate()
        is_feature_enabled = feature_handler.is_feature_enabled(feature_name)
        self.assertEqual(is_feature_enabled, True)

    @parameterized.expand(
        execution_envs_not_enabled_lambda_marshaller_ensure_ascii_false
    )
    def test_not_enabled_lambda_marshaller_ensure_ascii_false(self, execution_env):
        feature_handler = FeatureGate(execution_env=execution_env)
        is_feature_enabled = feature_handler.is_feature_enabled(
            "lambda_marshaller_ensure_ascii_false"
        )

        self.assertEqual(is_feature_enabled, False)

    @parameterized.expand(
        execution_envs_is_enabled_lambda_marshaller_ensure_ascii_false
    )
    def test_is_enabled_lambda_marshaller_ensure_ascii_false(self, execution_env):
        feature_handler = FeatureGate(execution_env=execution_env)
        is_feature_enabled = feature_handler.is_feature_enabled(
            "lambda_marshaller_ensure_ascii_false"
        )
        self.assertEqual(is_feature_enabled, True)
