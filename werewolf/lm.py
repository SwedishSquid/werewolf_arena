# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import dataclasses
import time
from typing import Any, Dict, List, Optional
import jinja2
from werewolf import utils
from werewolf.utils import Deserializable
from werewolf import apis
from werewolf.config import RETRIES
import jsonschema


@dataclasses.dataclass
class LmLog(Deserializable):
    prompt: str
    raw_resp: str
    result: Any
    model_id: str
    api_call_time: float
    retry_attempt: int
    call_successful: bool

    @classmethod
    def from_json(cls, data: Dict[Any, Any]):
        return cls(**data)


def format_prompt(prompt_template, worldstate) -> str:
    return jinja2.Template(prompt_template).render(worldstate)


def generate(
    prompt_template: str,
    response_schema: Dict[str, Any],
    worldstate: Dict[str, Any],
    model: str,
    temperature: float = 1.0,
    allowed_values: Optional[List[Any]] = None,
    result_key: Optional[str] = None,
) -> tuple[Any, LmLog]:
    """Generates text from the language model and parses the result.

    Args:
        prompt_template: The Jinja template for the prompt.
        response_schema: The schema for the expected response.
        worldstate: The world state to be rendered into the prompt.
        model: The language model to use.
        temperature: The sampling temperature for the language model.
        allowed_values: An optional list of allowed values for the result. If
          provided, the generation will retry until a result within the allowed
          values is obtained.
        result_key: An optional key to extract a specific value from the parsed
          result. If not provided, the entire parsed result is returned.

    Returns:
        A tuple containing the result (or None if unsuccessful) and the LmLog.
    """

    prompt = format_prompt(prompt_template, worldstate)
    raw_responses = []
    validation_error_msg = None
    for attempt in range(1, RETRIES + 1):
        raw_resp = None
        try:
            start_time = time.time()
            raw_resp = apis.generate(
                model=model,
                prompt=prompt,
                response_schema=response_schema,
                temperature=temperature,
                disable_recitation=True,
                disable_safety_check=True,
            )
            end_time = time.time()
            api_call_time = end_time - start_time

            result = utils.parse_json(raw_resp)
            # Validate against schema if result is not None
            if result is not None:
                try:
                    jsonschema.validate(instance=result, schema=response_schema)
                    validation_error_msg = None
                except jsonschema.ValidationError as ve:
                    validation_error_msg = str(ve)
                    print(f"Schema validation failed: {validation_error_msg}")
                    result = None
            else:
                validation_error_msg = "Parsing failed: result is None"

            log = LmLog(
                prompt=prompt,
                raw_resp=raw_resp,
                result=result,
                model_id=model,
                api_call_time=api_call_time,
                retry_attempt=attempt,
                call_successful=(result is not None),
            )

            if result and result_key:
                result = result.get(result_key)

            if result is not None and (
                allowed_values is None or result in allowed_values
            ):
                return result, log

        except Exception as e:
            print(f"Retrying due to Exception: {e}")
        temperature = min(1.0, temperature + 0.2)
        raw_responses.append(raw_resp)

    # If all attempts failed, log the final failed attempt
    fail_log = LmLog(
        prompt=prompt,
        raw_resp="-------".join(raw_responses),
        result=None,
        model_id=model,
        api_call_time=0.0,
        retry_attempt=RETRIES,
        call_successful=False,
    )
    if validation_error_msg:
        print(f"Final schema validation error: {validation_error_msg}")
        fail_log.result = {"validation_error": validation_error_msg}
    return None, fail_log
