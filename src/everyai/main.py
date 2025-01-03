import logging

from tqdm import tqdm

from everyai.classifier.sklearn_classifier import SklearnClassifer
from everyai.config.config import get_config
from everyai.data_loader.data_load import Data_loader
from everyai.data_loader.dataprocess import split_remove_stopwords_punctuation
from everyai.data_loader.everyai_dataset import EveryaiDataset
from everyai.data_loader.mongo_connection import get_mongo_connection
from everyai.everyai_path import (BERT_TOPIC_CONFIG_PATH, CLASSIFY_CONFIG_PATH,
                                  DATA_LOAD_CONFIG_PATH, DATA_PATH, FIG_PATH,
                                  GENERATE_CONFIG_PATH, MONGO_CONFIG_PATH)
from everyai.explanation.explain import LimeExplanation, ShapExplanation
from everyai.generator.generate import Generator
from everyai.topic.my_bertopic import create_topic

logging.basicConfig(level=logging.INFO)


def generate():
    generate_list_configs = get_config(GENERATE_CONFIG_PATH)
    logging.info("Generate configs: %s", generate_list_configs)
    data_list_configs = get_config(file_path=DATA_LOAD_CONFIG_PATH)
    logging.info("Data configs: %s", data_list_configs)
    for data_config in data_list_configs["data_list"]:
        for generate_config in generate_list_configs["generate_list"]:
            generator = Generator(config=generate_config)
            data_loader = Data_loader(
                data_name=data_config["data_name"],
                question_column=data_config["question_column"],
                answer_column=data_config["answer_column"],
                file_path=data_config["file_path"],
                data_type=data_config["data_type"],
            )
            qa_datas = data_loader.load_data2list(
                max_count=data_config["max_count"]
            )
            everyai_dataset = EveryaiDataset(
                dataname=data_config["data_name"],
                ai_list=[generate_config["model_name"]],
            )
            for data in tqdm(
                qa_datas, desc="Generating data", total=len(qa_datas)
            ):
                ai_response: str = generator.generate(data["question"])
                everyai_dataset.insert_ai_response(
                    question=data["question"],
                    ai_name=generate_config["model_name"],
                    ai_response=ai_response,
                )
                everyai_dataset.insert_human_response(
                    question=data["question"], human_response=data["answer"]
                )
                everyai_dataset.save(
                    path_or_database=DATA_PATH / everyai_dataset.data_name,
                    formatter="csv",
                )
                mongodb_config = get_config(MONGO_CONFIG_PATH)
                db = get_mongo_connection(**mongodb_config)
                everyai_dataset.save(path_or_database=db, formatter="mongodb")


def topic():
    data_list_configs = get_config(file_path=DATA_LOAD_CONFIG_PATH)
    logging.info("Data config: %s", data_list_configs)
    for data_config in data_list_configs["data_list"]:
        everyai_dataset = EveryaiDataset(
            dataname=data_config["data_name"],
            language=data_config["language"],
        )
        everyai_dataset.load(formatter="csv")
        logging.info("Loaded data: %s", everyai_dataset.data_name)
        topic_config = get_config(file_path=BERT_TOPIC_CONFIG_PATH)
        for catogeory in everyai_dataset.ai_list + ["human"]:
            logging.info("Category: %s", catogeory)
            docs = everyai_dataset.datas[catogeory].tolist()
            logging.info("Number of documents: %d", len(docs))
            new_docs = [
                split_remove_stopwords_punctuation(
                    doc, language=everyai_dataset.language
                )
                for doc in docs
            ]
            create_topic(
                docs=new_docs,
                output_folder=FIG_PATH / everyai_dataset.data_name / catogeory,
                topic_config=topic_config,
            )
            logging.info("Topic created for %s", catogeory)


def classify():
    data_list_configs = get_config(file_path=DATA_LOAD_CONFIG_PATH)
    logging.info("Data config: %s", data_list_configs)
    for data_config in data_list_configs["data_list"]:
        everyai_dataset = EveryaiDataset(
            dataname=data_config["data_name"],
            language=data_config["language"],
        )
        everyai_dataset.load(formatter="mongodb")
        logging.info("Loaded data: %s", everyai_dataset.data_name)
        texts, labels = everyai_dataset.get_records_with_1ai(
            ["THUDM/glm-4-9b-chat-hf"]
        )
        for classify_config in get_config(file_path=CLASSIFY_CONFIG_PATH)[
            "classifier_list"
        ]:
            match classify_config["classifier_type"]:
                case "sklearn":
                    text_classifier = SklearnClassifer(
                        **classify_config,
                    )
                case _:
                    raise ValueError("Classifier type not supported")
            text_classifier.load_data(
                texts, labels, data_name=everyai_dataset.data_name
            )
            text_classifier.train()
            text_classifier.test()
            text_classifier.save_model()
            text_classifier.show_score()
            logging.info("Model saved for %s", classify_config["model_name"])
            lime_explanation = LimeExplanation(classifier=text_classifier)
            lime_explanation.explain()
            shap_explanation = ShapExplanation(classifier=text_classifier)
            shap_explanation.explain()


def main():
    # generate()
    # topic()
    classify()


if __name__ == "__main__":
    main()
