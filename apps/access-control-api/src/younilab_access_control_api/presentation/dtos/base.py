from pydantic import BaseModel, ConfigDict


def _camel_case(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class ApiModel(BaseModel):
    """將 snake_case 欄位以 camelCase JSON 呈現的 schema 基底。"""

    model_config = ConfigDict(
        alias_generator=_camel_case,
        populate_by_name=True,
    )


class ApiRequest(ApiModel):
    """拒絕未知 JSON 欄位的 request schema 基底。"""

    model_config = ConfigDict(
        alias_generator=_camel_case,
        populate_by_name=True,
        extra="forbid",
    )
