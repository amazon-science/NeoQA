import os
from typing import Optional
import logging

# External Dependencies:
import boto3
from botocore.config import Config

logger = logging.getLogger(__name__)


class BedrockHelper:
    def __init__(self, model) -> None:

        self.bedrock_runtime = self.get_bedrock_client(
            assumed_role=os.environ.get("BEDROCK_ASSUME_ROLE", None),
            region=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
        )
        self.model = model

    def get_bedrock_client(
        self,
        assumed_role: Optional[str] = None,
        region: Optional[str] = None,
        runtime: Optional[bool] = True,
    ):
        if region is None:
            target_region = os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION"))
        else:
            target_region = region

        session_kwargs = {"region_name": target_region}
        client_kwargs = {**session_kwargs}

        profile_name = os.environ.get("AWS_PROFILE")
        if profile_name:
            print(f"  Using profile: {profile_name}")
            session_kwargs["profile_name"] = profile_name

        retry_config = Config(
            region_name=target_region,
            retries={
                "max_attempts": 1000,
                "mode": "standard",
            },
        )
        session = boto3.Session(**session_kwargs)

        if assumed_role:
            print(f"  Using role: {assumed_role}", end="")
            sts = session.client("sts")
            response = sts.assume_role(RoleArn=str(assumed_role), RoleSessionName="langchain-llm-1")
            print(" ... successful!")
            client_kwargs["aws_access_key_id"] = response["Credentials"]["AccessKeyId"]
            client_kwargs["aws_secret_access_key"] = response["Credentials"]["SecretAccessKey"]
            client_kwargs["aws_session_token"] = response["Credentials"]["SessionToken"]

        if runtime:
            service_name = "bedrock-runtime"
        else:
            service_name = "bedrock"

        bedrock_client = session.client(
            service_name=service_name, config=retry_config, **client_kwargs
        )

        return bedrock_client
