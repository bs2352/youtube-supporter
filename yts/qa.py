from typing import Optional, List, Generator, Tuple
import os
import logging
from concurrent.futures import ThreadPoolExecutor
import sys
import time
import asyncio

from llama_index import GPTVectorStoreIndex, Document, ServiceContext, LLMPredictor, LangchainEmbedding
from llama_index.indices.query.base import BaseQueryEngine
from llama_index.response.schema import RESPONSE_TYPE
from llama_index.schema import NodeWithScore
from youtube_transcript_api import YouTubeTranscriptApi
from pytube import YouTube
from langchain import LLMChain, PromptTemplate
from langchain.schema import LLMResult, ChatGeneration

from .types import TranscriptChunkModel, YoutubeTranscriptType
from .utils import setup_llm_from_environment, setup_embedding_from_environment, divide_transcriptions_into_chunks
from .summarize import get_summary



RUN_MODE_SEARCH  = 0x01
RUN_MODE_SUMMARY = 0x02

WHICH_RUN_MODE_PROMPT_TEMPLATE  = """「{title}」というタイトルの動画から次の質問に回答してください。

質問：{question}
"""
WHICH_RUN_MODE_PROMPT_TEMPLATE_VARIABLES = ["title", "question"]
WHICH_RUN_MODE_FUNCTIONS = [
    {
        "name": "answer_question_about_specific_things",
        "description": "Answer questions about specific things mentioned in a given video",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "動画のタイトル"
                },
                "question": {
                    "type": "string",
                    "description": "質問",
                }
            },
            "required": ["title", "question"]
        }
    },
    {
        "name": "answer_question_about_general_content",
        "description": "View the entire video and Answer questions about the general content of a given video",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "動画のタイトル",
                },
                "question": {
                    "type": "string",
                    "description": "質問",
                }
            },
            "required": ["title", "question"]
        }
    },
]


QA_PROMPT_TEMPLATE = """{question}
以下の文書の内容から回答してください。

{summary}
"""
QA_PROMPT_TEMPLATE_VARIABLES = ["question", "summary"]


class YoutubeQA:
    def __init__(self,
                 vid: str = "",
                 ref_sources: int = 3,
                 detail: bool = False,
                 debug: bool = False
    ) -> None:
        if vid == "":
            raise ValueError("video id is invalid.")

        self.vid: str = vid
        self.ref_source: int = ref_sources
        self.detail: bool = detail
        self.debug: bool = debug
        self.url: str = f'https://www.youtube.com/watch?v={vid}'
        self.title: str = ""

        self.index_dir: str = f'{os.environ["INDEX_STORE_DIR"]}/{self.vid}'
        self.service_context: ServiceContext = self._setup_llm()

        self.index: Optional[GPTVectorStoreIndex] = None
        self.query_response: Optional[RESPONSE_TYPE] = None

        self.loading_canceled: bool = False


    def _setup_llm (self) -> ServiceContext:
        llm = setup_llm_from_environment()
        embedding = setup_embedding_from_environment()
        llm_predictor: LLMPredictor = LLMPredictor(llm=llm)
        embedding_llm: LangchainEmbedding = LangchainEmbedding(embedding)
        service_context: ServiceContext = ServiceContext.from_defaults(
            llm_predictor = llm_predictor,
            embed_model = embedding_llm,
        )
        return service_context


    def _debug (self, message: str, end: str = "\n", flush: bool = False) -> None:
        if self.debug is False:
            return
        print(message, end=end, flush=flush)
        return


    def prepare_query (self) -> None:
        self.title = YouTube(self.url).vid_info["videoDetails"]["title"]
        self.index = self._load_index() if os.path.isdir(self.index_dir) else \
                     self._create_index()


    def _load_index (self) -> GPTVectorStoreIndex:
            from llama_index import StorageContext, load_index_from_storage
            self._debug(f'load index from {self.index_dir} ...', end="", flush=True)
            storage_context: StorageContext = StorageContext.from_defaults(persist_dir=self.index_dir)
            index: GPTVectorStoreIndex = load_index_from_storage(storage_context, service_context=self.service_context) # type: ignore
            self._debug("fin", flush=True)
            return index


    def _create_index (self) -> GPTVectorStoreIndex:

        # 本にある楽ちんバージョン（使わない）
        # テキストしか取得できず、また後々開始時刻も利用したいのでチャンク分割を自作する
        # YoutubeTranscriptReader = download_loader("YoutubeTranscriptReader")
        # loader = YoutubeTranscriptReader()
        # documents = loader.load_data(ytlinks=["https://www.youtube.com/watch?v=cEynsEWpXdA"], languages=["ja"]) # MS2
        # documents = loader.load_data(ytlinks=["https://www.youtube.com/watch?v=tFgqdHKsOME"], languages=["ja"]) # MS
        # documents = loader.load_data(ytlinks=["https://www.youtube.com/watch?v=Tia4YJkNlQ0"], languages=["ja"]) # 西園寺
        # documents = loader.load_data(ytlinks=["https://www.youtube.com/watch?v=oc6RV5c1yd0"])
        # documents = loader.load_data(ytlinks=["https://www.youtube.com/watch?v=XJRoDEctAwA"])
        # for doc in documents:
        #     print(doc.text, '-------------------')

        self._debug("creating index ...", end="", flush=True)

        MAXLENGTH = 300
        OVERLAP_LENGTH = 3
        transcriptions: List[YoutubeTranscriptType] = YouTubeTranscriptApi.get_transcript(video_id=self.vid, languages=["ja", "en", "en-US"])
        chunks: List[TranscriptChunkModel] = divide_transcriptions_into_chunks(
            transcriptions,
            maxlength = MAXLENGTH,
            overlap_length = OVERLAP_LENGTH,
            id_prefix = self.vid
        )

        documents = [
            Document(text=chunk.text.replace("\n", " "), doc_id=chunk.id) for chunk in chunks
        ]

        index: GPTVectorStoreIndex = GPTVectorStoreIndex.from_documents(documents, service_context=self.service_context)

        self._debug("fin", flush=True)

        # ディスクに保存しておく
        self._debug(f'save index to {self.index_dir} ...', end="", flush=True)
        if not os.path.isdir(self.index_dir):
            os.makedirs(self.index_dir)
        index.storage_context.persist(persist_dir=self.index_dir)
        self._debug("fin", flush=True)

        return index


    def run_query (self, query: str) -> str:
        """（メモ）
        メインスレッドでQAを行う
        loadingは別スレッドで実行しQAが終われば停止する
        """
        answer: str = ""
        with ThreadPoolExecutor(max_workers=1) as executor:
            future_loading = executor.submit(self._loading)
            try:
                answer = self._run_query(query)
            except:
                pass
            self.loading_canceled = True
            while future_loading.done() is False:
                time.sleep(1)

        return answer


    def _run_query (self, query: str) -> str:
        if self.index is None:
            return ""
        answer: str = ""
        mode: int = self._which_run_mode(query)
        if mode == RUN_MODE_SEARCH:
            answer = self._search_and_answer(query)
        if mode == RUN_MODE_SUMMARY:
            answer = self._summarize_and_answer(query)

        return answer


    def _which_run_mode (self, query: str) -> int:
        if query == "":
            return RUN_MODE_SUMMARY

        llm = setup_llm_from_environment()
        prompt = PromptTemplate(
            template=WHICH_RUN_MODE_PROMPT_TEMPLATE,
            input_variables=WHICH_RUN_MODE_PROMPT_TEMPLATE_VARIABLES
        )
        chain = LLMChain(
            llm=llm,
            prompt=prompt,
            llm_kwargs={
                "functions": WHICH_RUN_MODE_FUNCTIONS
            },
            output_key="function",
            verbose=True
        )
        result: LLMResult = chain.generate([{"title": self.title, "question": query}])
        generation: ChatGeneration = result.generations[0][0] # type: ignore
        message = generation.message.additional_kwargs
        func_name = WHICH_RUN_MODE_FUNCTIONS[0]["name"]
        if "function_call" in message:
            func_name = message["function_call"]["name"]

        return RUN_MODE_SEARCH if func_name == WHICH_RUN_MODE_FUNCTIONS[0]["name"] else \
               RUN_MODE_SUMMARY


    def _search_and_answer (self, query: str) -> str:
        if self.index is None:
            return ""

        # より詳細にクエリエンジンを制御したい場合は以下を参照
        # https://gpt-index.readthedocs.io/en/v0.6.26/guides/primer/usage_pattern.html
        query_engine: BaseQueryEngine = self.index.as_query_engine(similarity_top_k=self.ref_source)
        response: RESPONSE_TYPE = query_engine.query(query)
        self.query_response = response

        return str(self.query_response).strip()


    def _summarize_and_answer (self, query: str) -> str:
        summary: str = get_summary(self.vid)
        llm = setup_llm_from_environment()
        prompt = PromptTemplate(
            template=QA_PROMPT_TEMPLATE,
            input_variables=QA_PROMPT_TEMPLATE_VARIABLES
        )
        chain = LLMChain(
            llm=llm,
            prompt=prompt,
            # verbose=True
        )
        answer: str  = chain.run(question=query, summary=summary)
        return answer


    def _loading (self):
        chars = [
            '/', '―', '\\', '|', '/', '―', '\\', '|', '😍',
            '/', '―', '\\', '|', '/', '―', '\\', '|', '🤪',
            '/', '―', '\\', '|', '/', '―', '\\', '|', '😎',
        ]
        self.loading_canceled = False
        i = 0
        while i >= 0:
            i %= len(chars)
            sys.stdout.write("\033[2K\033[G %s " % chars[i])
            sys.stdout.flush()
            time.sleep(1.0)
            i += 1
            if self.loading_canceled is True:
                break
        sys.stdout.write("\033[2K\033[G")
        sys.stdout.flush()
        return


    def get_source (self) -> Generator[Tuple[float, str, str, str], None, None]:
        if self.query_response is None:
            return None

        def _id2time (id: str) -> str:
            sec: int = int(float(id.rsplit('-', 1)[1]))
            s = sec % 60
            m = (sec // 60) % 60
            h = (sec // 60) // 60
            return f'{h}:{m}:{s}'
        
        # 暫定版（もっと良い取り方があるはず）
        def _get_id (node: NodeWithScore) -> str:
            id = ""
            for _, val in node.node.dict()["relationships"].items():
                if "node_id" in val.keys():
                    id = val["node_id"]
            return id

        for node in self.query_response.source_nodes:
            id = _get_id(node)
            score: float = node.score if node.score is not None else 0.0
            source: str = node.node.get_content()
            yield score, id, _id2time(id), source


