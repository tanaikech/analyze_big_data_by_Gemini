import io
import json
import os
import time
from google import genai
from google.genai.types import GenerateContentConfig
from google.api_core import retry


class AnalyzeBigData:
    """
    It processes large amounts of data by splitting it into chunks and generating content using the Gemini API for each chunk. It saves intermediate results to a temporary local file for resuming.
    """

    def __init__(self) -> None:
        self.__client = None
        self.__model_name = None
        self.__config = None
        self.__prompt = None
        self.__temp_file_path = "./temp.txt"
        self.__limit_length = 500000  # Default chunk size is 500,000 bytes.
        self.__disp_generated_content = False
        self.__specific_chunks = []

        class Color:
            red = "\033[31m"
            green = "\033[32m"
            yellow = "\033[33m"
            blue = "\033[34m"
            cyan = "\033[36m"
            magenta = "\033[35m"
            clear = "\033[0m"

        self.__color = Color

    def run(self, object: dict) -> list[str | list | dict]:
        """
        Main method.

        Args:
            object: A dictionary containing parameters:
                api_key (str): Your API key for using the Gemini API. (Required)
                model (str): The name of the Gemini model to use (e.g., "gemini-2.5-flash-preview-04-17").
                             The default model is "gemini-2.5-flash-preview-04-17".
                data (list[str | dict | list]): The large list of data objects to process. (Required)
                prompt (str): The prompt for the Gemini model. (Required)
                limit_length (int): The approximate maximum JSON string length for each data chunk.
                                    The default value is 500000.
                response_mime_type (str): The desired MIME type for the response (e.g., "application/json").
                                          The default mimeType is "text/plain".
                response_schema (dict): A schema for the expected response format.
                temp_file (str): Filename of the temporal file. This temporal file is used for resuming. The default is "./temp.txt"
                disp_generated_content (boolean): The default is False. When this is True, the generated content is shown in the terminal.
                specific_chunks (list): Chunk numbers that the start is 1. You can generate content for the specific chunks using this property.

        Returns:
            list: A list containing the generated content for each processed chunk.

        Raises:
            ValueError: If apiKey or prompt is missing from the params.
            Exception: Propagates exceptions that occur during file operations or API calls.
        """

        print(f"{self.__color.green}AnalyzeBirgData... start{self.__color.clear}")
        self._setInstances(object)

        data = object.get("data", [])
        if not data:
            raise ValueError(f"{self.__color.red}'data' is empty.{self.__color.clear}")
        if not isinstance(data, list):
            raise ValueError(
                f"{self.__color.red}'data' is required to be a list.{self.__color.clear}"
            )

        self.__limit_length = object.get("limit_length", 500000)
        temp_data = self._loadTempFile()
        arr = self._dataChunking(data, temp_data)
        res = self._processChunks(arr, temp_data)
        print(f"{self.__color.green}AnalyzeBirgData... end{self.__color.clear}")
        return res

    def _setInstances(self, object: dict) -> None:
        api_key = object.get("api_key")
        self.__prompt = object.get("prompt", None)
        self.__temp_file_path = object.get("temp_file", "./temp.txt")

        if not api_key:
            raise ValueError(
                f"{self.__color.red}Parameter 'apiKey' is required.{self.__color.clear}"
            )
        if self.__prompt is None:
            raise ValueError(
                f"{self.__color.red}Parameter 'prompt' is required.{self.__color.clear}"
            )

        self.__client = genai.Client(api_key=api_key)
        self.__model_name = object.get("model", "models/gemini-2.5-flash-preview-04-17")
        response_mime_type = object.get("response_mime_type", "text/plain")
        self.__config = GenerateContentConfig(response_mime_type=response_mime_type)
        response_schema = object.get("response_schema", None)
        if response_schema is not None:
            self.__config = GenerateContentConfig(
                response_mime_type=response_mime_type, response_schema=response_schema
            )
        self.__disp_generated_content = object.get("disp_generated_content", False)
        self.__specific_chunks = object.get("specific_chunks", [])

    def _loadTempFile(self) -> list:
        temp_data = []
        if os.path.exists(self.__temp_file_path):
            try:
                with open(self.__temp_file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    if content:
                        temp_data = json.loads(content)
                    else:
                        temp_data = []
                if not isinstance(temp_data, list):
                    temp_data = []
            except json.JSONDecodeError:
                temp_data = []
            except Exception as e:
                temp_data = []
        print(
            f"Length of tempData (from '{self.__temp_file_path}') is {len(temp_data)}."
        )
        return temp_data

    def _dataChunking(self, data: list, temp_data: list) -> list:
        print(f"{self.__color.green}Data chunking... start{self.__color.clear}")
        arr = []
        temp = []
        for i, element in enumerate(data):
            temp.append(element)
            temp_text = json.dumps(temp)
            is_last_element = i == len(data) - 1
            if len(temp_text) > self.__limit_length or (
                is_last_element and len(temp) > 0
            ):
                if len(temp) > 0:
                    arr.append(temp)
                temp = []

        if len(temp) > 0:
            arr.append(temp)

        print(
            f"{self.__color.yellow}The input data ({len(data)}) was divided into {len(arr)} chunks.{self.__color.clear}"
        )

        if len(arr) > 0:
            print(
                f"{self.__color.yellow}Gemini API calls will be attempted for {len(arr) - len(temp_data)} new chunks (total {len(arr)}).{self.__color.clear}"
            )
        else:
            print("No data chunks to process.")

        print(f"{self.__color.green}Data chunking... end{self.__color.clear}")
        return arr

    def _uploadFile(self, text: str) -> dict:
        print(f"{self.__color.green}Upload chunk... start{self.__color.clear}")
        fileContent = io.BytesIO(text.encode())
        uploaded_file = self.__client.files.upload(
            file=fileContent, config={"mime_type": "text/plain"}
        )
        while uploaded_file.state.name == "PROCESSING":
            print(f"{self.__color.yellow}Waiting...{self.__color.clear}")
            time.sleep(3)
            uploaded_file = self.__client.files.get(name=uploaded_file.name)
        print(f"{self.__color.green}Upload chunk... end{self.__color.clear}")
        return uploaded_file

    @retry.Retry(initial=30)
    def _generate_content(self, contents: list) -> dict:
        return self.__client.models.generate_content(
            model=self.__model_name, contents=contents, config=self.__config
        )

    def _processChunk(
        self, i: int, arr_len: int, d_chunk: str | list, temp_data: list
    ) -> list:
        chunk_number = i + 1
        print(f"\n### Processing chunk {chunk_number} / {arr_len}...")

        data_chunk = ""
        if (
            isinstance(d_chunk, str)
            or isinstance(d_chunk, int)
            or isinstance(d_chunk, float)
        ):
            data_chunk = d_chunk
        if isinstance(d_chunk, list) or isinstance(d_chunk, dict):
            data_chunk = json.dumps(d_chunk)

        uploaded_file = self._uploadFile(data_chunk)

        contents = [uploaded_file, {"text": self.__prompt}]

        try:
            response = self.__client.models.count_tokens(
                model=self.__model_name, contents=contents
            )
            print(f"Total tokens: {response.total_tokens}")
            print(f"{self.__color.cyan}Generating content... start{self.__color.clear}")
            response = self._generate_content(contents)
            print(f"{self.__color.cyan}Generating content... end{self.__color.clear}")
            generated_content = None
            if response and response.candidates:
                candidate = response.candidates[0]
                if candidate.content and candidate.content.parts:
                    generated_content = "".join(
                        part.text for part in candidate.content.parts if part.text
                    )
                elif candidate.finish_reason:
                    print(
                        f"Warning: API call for chunk {chunk_number} finished with reason: {candidate.finish_reason}. No content generated."
                    )
                else:
                    print(
                        f"Warning: API call for chunk {chunk_number} returned no content or finish reason."
                    )

            if self.__disp_generated_content:
                print("--- Generated content --- start")
                print(
                    generated_content
                    if generated_content is not None
                    else "[No content generated]"
                )
                print("--- Generated content --- end")

            self.__client.files.delete(name=uploaded_file.name)

            try:
                generated_content = json.loads(generated_content)
                print(
                    f"{self.__color.yellow}Generated content is in JSON format.{self.__color.clear}"
                )
            except json.JSONDecodeError as e:
                print(
                    f"{self.__color.yellow}Generated content is not in JSON format.{self.__color.clear}"
                )

            temp_data.append(generated_content)
            try:
                with open(self.__temp_file_path, "w", encoding="utf-8") as f:
                    json.dump(temp_data, f, indent=2)
                print(
                    f"Saved temporary data to '{self.__temp_file_path}'. Current length: {len(temp_data)}."
                )
            except Exception as e:
                print(
                    f"Error saving temporary data to '{self.__temp_file_path}' after processing chunk {chunk_number}: {e}"
                )
                raise e

            if i < arr_len - 1:
                time.sleep(10)

        except Exception as err:
            print(f"Error processing chunk {chunk_number}: {err}")
            print(f"{self.__color.red}{err.message}{self.__color.clear}")
            print("Retry! Wait for 30 seconds.")
            time.sleep(30)
            self._processChunk(i, arr_len, d_chunk, temp_data)

        return temp_data

    def _processChunks(self, arr: list, temp_data: list) -> list:
        print(f"{self.__color.green}Process chunk... start{self.__color.clear}")
        arr_len = len(arr)
        for i, d_chunk in enumerate(arr):
            chunk_number = i + 1
            if i < len(temp_data):
                print(
                    f"Skipped chunk {chunk_number}: Already processed (result found in temp_data)."
                )
                continue

            if len(self.__specific_chunks) > 0:
                if chunk_number not in self.__specific_chunks:
                    continue
                else:
                    print(
                        f"{self.__color.yellow}Generate content from chunk number '{chunk_number}' by the property of 'specific_chunks'.{self.__color.clear}"
                    )

            self._processChunk(i, arr_len, d_chunk, temp_data)

        print(f"{self.__color.green}Process chunk... end{self.__color.clear}")

        if len(temp_data) >= len(arr):
            try:
                os.remove(self.__temp_file_path)
                print(
                    f"\n{self.__color.green}All {len(arr)} chunks processed! Temporary file '{self.__temp_file_path}' is deleted.{self.__color.clear}"
                )
            except OSError as e:
                print(f"Error deleting temporary file '{self.__temp_file_path}': {e}")
        elif len(self.__specific_chunks) == 0:
            print(
                f"\n{self.__color.red}Processing finished, but only {len(temp_data)} out of {len(arr)} chunks were processed.{self.__color.clear}"
            )
            print(
                f"{self.__color.red}Temporary file '{self.__temp_file_path}' remains and can be used to resume.{self.__color.clear}"
            )
        elif len(self.__specific_chunks) > 0:
            print(
                f"\n{self.__color.yellow}Processing finished! Generated content by 'specific_chunks'. Temporary file '{self.__temp_file_path}' is deleted.{self.__color.clear}"
            )
            os.remove(self.__temp_file_path)

        return temp_data
