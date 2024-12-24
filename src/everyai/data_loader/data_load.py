import logging
from pathlib import Path
from typing import Callable

import pandas as pd
from datasets import load_dataset

from everyai.data_loader.filter import default_filter
from everyai.everyai_path import DATA_PATH


class Data_loader:
    def __init__(
        self,
        data_name: str,
        question_column: str = "question",
        answer_column: str = "answer",
        file_path: str | Path = None,
        data_type: str = None,
        filter: Callable[[pd.DataFrame], pd.DataFrame] = None,
    ):
        self.data_name = data_name
        if file_path is None:
            self.file_name_or_path = DATA_PATH / data_name
        else:
            self.file_name_or_path = file_path
        if data_type is None:
            self.file_type = Path(self.file_name_or_path).suffix
        else:
            self.file_type = data_type
        self.question_column = question_column
        self.answer_column = answer_column
        self.filter = filter

    def load_data2list(self, max_count: int = None):
        if Path(self.file_name_or_path).exists() or self.file_type == "huggingface":
            match self.file_type:
                case "csv":
                    data = pd.read_csv(self.file_name_or_path)
                case "xlsx":
                    data = pd.read_excel(self.file_name_or_path)
                case "jsonl":
                    data = pd.read_json(self.file_name_or_path, lines=True)
                case "json":
                    data = pd.read_json(self.file_name_or_path)
                case "huggingface":
                    data = load_dataset(path=self.file_name_or_path)[
                        "train"
                    ].to_pandas()
                case _:
                    logging.error("Invalid file format")
        else:
            if not Path(self.file_name_or_path).exists():
                logging.error(f"File not found: {self.file_name_or_path}")
            else:
                logging.error("Invalid file type")
        if self.filter is not None:
            data = self.filter(data)
        else:
            data = default_filter(data)
            logging.info(
                (
                    "Default filter is applied, if you want to apply custom filter, "
                    "please provide the filter function"
                )
            )
        if max_count is not None and data is not None:
            data = data.head(max_count)
        else:
            logging.info("Max count is None and all the records will be loaded")
        data.rename(
            columns={
                self.question_column: "question",
                self.answer_column: "answer",
            },
            inplace=True,
        )
        return data[["question", "answer"]].to_dict(orient="records")

    def apply_filter(self, data: pd.DataFrame) -> pd.DataFrame:
        if self.filter is not None:
            return data[data.apply(self.filter, axis=1)]
        return data


if __name__ == "__main__":
    # loader = Data_loader("test.csv", "question")
    # data = loader.load_data()
    # print(data)
    # loader = Data_loader("test.xlsx", "question")
    # data = loader.load_data()
    # print(data)
    # loader = Data_loader("test.jsonl", "question")
    # data = loader.load_data()
    # print(data)
    # loader = Data_loader("test.json", "question")
    # data = loader.load_data()
    # print(data)
    loader = Data_loader("wanghw/human-ai-comparison", "question")
    data = loader.load_data2list()
    print(data)
    loader = Data_loader("test.invalid", "question")
    data = loader.load_data2list()
    print(data)
