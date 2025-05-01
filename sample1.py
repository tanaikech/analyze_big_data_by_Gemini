from analyze_big_data_by_Gemini import AnalyzeBigData
import json
import os


api_key = "###" # Please set your API key
filename = "###" # Please set your filename of file of the big data.
file_path = os.path.join("./", filename) # Please set your path of the file.

prompt = "Summarize data." # Please set your prompt

data = []
with open(file_path, "r", encoding="utf-8") as f:
    data = json.loads(f.read())

object = {
    "api_key": api_key,
    "data": data,
    "prompt": prompt,
}

l = 0
res = []
while len(res) != 1:
    l += 1
    print(f"\n\n### Loop: {l}")
    res = AnalyzeBigData().run(object)
    object["data"] = res
    print(f"Number of chunks: {len(res)}")

print(res[0])
with open(os.path.join("./", "Result_" + filename), "w", encoding="utf-8") as f:
    f.write(res[0])
