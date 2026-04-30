# prompt 定义与渲染

LLM_ROUTER_PROMPT = """你是一个问题路由器，需要判断用户问题应进入知识库问答还是普通对话。

分类规则：
- knowledge_qa：问题需要依赖项目文档、业务流程、配置说明、代码路径、历史资料或知识库内容才能准确回答。
- chat_qa：问题是普通闲聊、通用知识、无需检索文档即可回答。

用户问题：
{query}

只返回以下两个分类之一，不要解释：
- knowledge_qa
- chat_qa
"""


LLM_DOC_DEPEND_PROMPT = """你是一个 RAG 文档相关性评测专家，需要判断检索到的文档片段是否足以支撑答案。

请基于以下三部分内容进行评估：

用户原始问题：
{query}

向量检索得到的文档片段：
{embed_doc}

大模型基于上述文档生成的答案：
{llm_reason_res}

评估标准：
1. 如果文档片段与用户问题主题一致，且足以支撑答案，返回 resolve。
2. 如果文档片段明显偏题、信息不足、无法支撑答案，返回 reject，并重写一个更适合检索的 query。
3. 重写 query 时需保留用户问题的核心意图、关键实体、业务场景和限制条件。

只返回 JSON，不要输出额外解释。

通过时返回：
{{
  "score": "resolve",
  "query": ""
}}

相关性过低时返回：
{{
  "score": "reject",
  "query": "重写后的用户问题"
}}
"""

KNOWLEDGE_QA_SYSTEM_PROMPT = """你是一个严谨的知识库问答助手，当前处于 knowledge_qa 场景。

回答要求：
1. 优先依据给定参考资料回答用户问题。
2. 如果参考资料能支撑答案，请直接给出清晰、结构化的回答。
3. 如果参考资料只覆盖部分信息，请明确说明哪些内容可由资料支持、哪些内容资料不足。
4. 如果参考资料完全无法回答问题，请明确说明资料不足，不要编造。
"""

KNOWLEDGE_QA_USER_PROMPT = """用户问题：
{query}

参考资料：
{context}
"""

CHAT_QA_SYSTEM_PROMPT = """你是一个普通对话助手，当前处于 chat_qa 场景。

回答要求：
1. 直接回答用户问题。
2. 不要假装已经查询知识库或参考资料。
3. 如果问题涉及项目文档、业务流程、配置说明、代码路径或历史资料，应提示该问题更适合进入知识库问答。
"""


class PromptManager:
    def __init__(
        self,
        router_prompt: str = LLM_ROUTER_PROMPT,
        doc_depend_prompt: str = LLM_DOC_DEPEND_PROMPT,
        knowledge_qa_system_prompt: str = KNOWLEDGE_QA_SYSTEM_PROMPT,
        knowledge_qa_user_prompt: str = KNOWLEDGE_QA_USER_PROMPT,
        chat_qa_system_prompt: str = CHAT_QA_SYSTEM_PROMPT,
    ):
        self.router_prompt = router_prompt
        self.doc_depend_prompt = doc_depend_prompt
        self.knowledge_qa_system_prompt = knowledge_qa_system_prompt
        self.knowledge_qa_user_prompt = knowledge_qa_user_prompt
        self.chat_qa_system_prompt = chat_qa_system_prompt

    def build_router_prompt(self, query: str) -> str:
        return self.router_prompt.format(query=query)

    def build_doc_depend_prompt(self, query: str, embed_doc, llm_reason_res) -> str:
        return self.doc_depend_prompt.format(
            query=query,
            embed_doc=embed_doc,
            llm_reason_res=llm_reason_res,
        )

    def build_knowledge_qa_messages(self, query: str, context: str):
        return [
            {"role": "system", "content": self.knowledge_qa_system_prompt},
            {
                "role": "user",
                "content": self.knowledge_qa_user_prompt.format(
                    query=query,
                    context=context,
                ),
            },
        ]

    def build_chat_qa_messages(self, query: str):
        return [
            {"role": "system", "content": self.chat_qa_system_prompt},
            {"role": "user", "content": query},
        ]
