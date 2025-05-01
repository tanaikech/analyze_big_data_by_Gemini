from analyze_big_data_by_Gemini import AnalyzeBigData
import json


api_key = "###" # Please set your  API key.
data = [,,,] # Please set your data.

sample_json_schema = {
    "title": "Sample Data Schema",
    "description": "Sample description",
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "key1": {"type": "string", "description": "Sample description"},
            "key2": {"type": "number", "description": "Sample description"},
        },
        "required": ["key1", "key2"],
    },
}
sample_response_schema = {
    "type": "object",
    "properties": {"content": {"type": "string", "description": "Generated content"}},
}
object = {
    "api_key": api_key,
    "data": data,
    "prompt": f"JSON schema of given data is as follows. <JSONSchema>${json.dumps(sample_json_schema)}</JSONSchema> Summarize the data.",
    "response_schema": sample_response_schema,
}
res = AnalyzeBigData().run(object)
