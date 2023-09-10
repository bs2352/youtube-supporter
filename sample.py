import os
# from llama_index import download_loader, GPTVectorStoreIndex, Document
# from youtube_transcript_api import YouTubeTranscriptApi
import openai
import dotenv
import sys


DEFAULT_VID = "cEynsEWpXdA"
dotenv.load_dotenv()

# INDEX_STORAGE_DIR = "./indexes"
# if not os.path.isdir(INDEX_STORAGE_DIR):
#     os.mkdir(INDEX_STORAGE_DIR)


# dotenv.load_dotenv()
# OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
# os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
# openai.api_key = OPENAI_API_KEY


# video_id = "Tia4YJkNlQ0"
# video_id = "cEynsEWpXdA"

def get_transcription ():
    from youtube_transcript_api import YouTubeTranscriptApi

    # YoutubeTranscriptReader = download_loader("YoutubeTranscriptReader")
    # loader = YoutubeTranscriptReader()
    # documents = loader.load_data(ytlinks=["https://www.youtube.com/watch?v=cEynsEWpXdA"], languages=["ja"]) # MS2
    # documents = loader.load_data(ytlinks=["https://www.youtube.com/watch?v=tFgqdHKsOME"], languages=["ja"]) # MS
    # documents = loader.load_data(ytlinks=["https://www.youtube.com/watch?v=Tia4YJkNlQ0"], languages=["ja"]) # 西園寺
    # documents = loader.load_data(ytlinks=["https://www.youtube.com/watch?v=oc6RV5c1yd0"])
    # documents = loader.load_data(ytlinks=["https://www.youtube.com/watch?v=XJRoDEctAwA"])
    # for doc in documents:
    #     print(doc.text, '-------------------')

    MAXLENGTH = 500
    scripts = YouTubeTranscriptApi.get_transcript(video_id=DEFAULT_VID, languages=["ja"])
    # text = ""
    for script in scripts:
        print(script)
        # text += script["text"].replace("\n", " ")
        # text += script["text"]
    # print(text)

# from langchain.text_splitter import CharacterTextSplitter, RecursiveCharacterTextSplitter
# from langchain.docstore.document import Document as LangChainDocument

# text_splitter = CharacterTextSplitter(
#     separator="\n",
#     chunk_size=300,
#     chunk_overlap=20
# )
# text_splitter = RecursiveCharacterTextSplitter(
#     chunk_size=500,
#     chunk_overlap=20,
# )
# texts = text_splitter.split_text(text)
# for t in texts:
#     print(t, len(t))
#     print('----')
# sys.exit()

# docs = [LangChainDocument(page_content=t) for t in texts]
# docs = [LangChainDocument(page_content=t) for i, t in enumerate(texts) if i < 3]


# from langchain.chains.summarize import load_summarize_chain
# from langchain.llms import OpenAI
# from langchain.chat_models import ChatOpenAI
# from langchain.prompts import PromptTemplate

# map_prompt_template = """以下の内容を簡潔にまとめてください。:


# "{text}"


# 簡潔な要約:"""
# map_prompt = PromptTemplate(template=map_prompt_template, input_variables=["text"])
# combine_prompt = map_prompt


# chain_type = "map_reduce"
# llm = OpenAI(
#     client=None,
#     model="text-davinci-003",
#     temperature=0.0,
#     # verbose=True,
#     max_tokens=1024,
# )
# llm = ChatOpenAI(
#     client=None,
#     model="gpt-3.5-turbo-16k",
#     temperature=0.0,
#     max_tokens=1024,
#     verbose=True,
# )
# chain = load_summarize_chain(
#     llm=llm,
#     chain_type=chain_type,
#     map_prompt=map_prompt,
#     combine_prompt=combine_prompt,
#     verbose=True
# )
# summarized_text = chain.run(docs)
# print(summarized_text)

# from langchain.embeddings import OpenAIEmbeddings
# from openai.embeddings_utils import cosine_similarity

# embeddings = OpenAIEmbeddings()
# doc_embeddings = embeddings.embed_documents(texts)

# prev_text = ""
# prev_embedding = [0.0e-10] * len(doc_embeddings[0])
# for text, embedding in zip(texts, doc_embeddings):
#     similarity = cosine_similarity(prev_embedding, embedding)
#     # print(text[:50], similarity, "###" if similarity < 0.80 else "")
#     if similarity < 0.80:
#         print(prev_text)
#         print(f'[{similarity}]------------')
#         print(text)
#         print('========')
#     prev_text = text
#     prev_embedding = embedding

def divide_topic ():
    from youtube_transcript_api import YouTubeTranscriptApi
    from langchain.prompts import PromptTemplate
    from langchain.chains import LLMChain
    from yts.utils import divide_transcriptions_into_chunks, setup_llm_from_environment

    transcriptions = YouTubeTranscriptApi.get_transcript(video_id=DEFAULT_VID, languages=["ja", "en"])
    chunks = divide_transcriptions_into_chunks(
        transcriptions=transcriptions,
        maxlength=300,
        overlap_length=0
    )
    # for chunk in chunks:
    #     print(chunk)

    prompt_template = \
"""以下に記載する文1と文2はYoutube動画の会話の一部を並べたもので、文2は文1に続く会話です。
文2は文1と同じ話題について述べられていますか？
それとも文2は文1とは異なる新たな話題について話されていますか？
文2が文1と同じ話題あればYes、異なる話題であればNoと回答してください。

文1:
{text1}

文2:
{text2}

回答:
"""
    # print(prompt_template)
    prompt = PromptTemplate(template=prompt_template, input_variables=["text1", "text2"])

    llm_chain = LLMChain(
        llm = setup_llm_from_environment(),
        prompt=prompt
    )


    prev_text_1 = ""
    prev_text_2 = ""
    for idx, chunk in enumerate(chunks):
        if idx == 0:
            prev_text_1 = prev_text_2
            prev_text_2 = chunk.text
            continue
        inputs = {
            "text1": f'{prev_text_1.strip()}\n{prev_text_2.strip()}',
            "text2": chunk.text,
        }
        # print(prompt.format(**inputs))
        result = llm_chain.predict(**inputs).strip()
        # if result == "Yes":
        if result == "No":
            print(prompt.format(**inputs))
            input()
        prev_text_1 = prev_text_2
        prev_text_2 = chunk.text
        # break
        # input()
        print(f".{result}", end="", flush=True)


def get_topic ():
    from youtube_transcript_api import YouTubeTranscriptApi
    from langchain.prompts import PromptTemplate
    from langchain.chains import LLMChain
    from yts.utils import divide_transcriptions_into_chunks, setup_llm_from_environment

    transcriptions = YouTubeTranscriptApi.get_transcript(video_id=DEFAULT_VID, languages=["ja", "en"])
    chunks = divide_transcriptions_into_chunks(
        transcriptions=transcriptions,
        maxlength=1000,
        overlap_length=5
    )
    # for chunk in chunks:
    #     print(chunk)

    prompt_template = \
"""私はYoutube動画のアジェンダを作成するために動画内で触れられているトピックをリストアップしています。
「文1」には会話の一部が記載されています。
「今までのとピック」には文1までに触れられていたトピックのリストが記載されています。
「文1」と「今までトピック」からこの動画で触れられているトピックを抽出してください。

今までのトピック:
{topics}

文1:
{text}

トピック:
"""
    # print(prompt_template)
    prompt = PromptTemplate(template=prompt_template, input_variables=["topics", "text"])

    llm_chain = LLMChain(
        llm = setup_llm_from_environment(),
        prompt=prompt
    )

    topics = ""
    for idx, chunk in enumerate(chunks):
        input = {
            "topics": topics,
            "text": chunk.text,
        }
        print(prompt.format(**input))
        result = llm_chain.predict(**input)
        print(result)
        topics = result
        # break
        # input()
        # if idx > 5:
        #     break


def get_topic_from_summary ():
    from langchain.prompts import PromptTemplate
    from langchain.chains import LLMChain
    from yts.utils import setup_llm_from_environment
    import json

    vid = DEFAULT_VID
    # vid = "Tia4YJkNlQ0"
    vid = "Bd9LWW4cxEU"
    with open(f"./summaries/{vid}", "r") as f:
        summary = json.load(f)

    prompt_template = \
"""私はYoutube動画のアジェンダを作成しています。
以下に記載する動画のタイトルと要約からアジェンダを作成してください。

タイトル:
{title}

要約:
{summaries}

アジェンダ:
"""
    # print(prompt_template)
    prompt = PromptTemplate(template=prompt_template, input_variables=["title", "summaries"])

    llm_chain = LLMChain(
        llm = setup_llm_from_environment(),
        prompt=prompt
    )

    summaries = ""
    for detail in summary["detail"]:
        summaries = f'{summaries}\n・{detail}'

    inputs = {
        "title": summary["title"],
        "summaries": summaries,
    }
    # print(prompt.format(**inputs))
    print(llm_chain.predict(**inputs))


if __name__ == "__main__":
    # get_transcription()
    # divide_topic()
    # get_topic()
    get_topic_from_summary()