// C:\Users\Owner\nova\static\js\chat-service.js

(() => {
  "use strict"

  function createChatService(options = {}) {
    const {
      state,
      api,
      elements = {},
    } = options

    if (!state) {
      throw new Error("NovaChatService: state is required")
    }

    const apiClient = api || window.NovaApp?.api || window.NovaAPI

    if (!apiClient) {
      throw new Error("NovaChatService: api is required")
    }

    const el = {
      chatList: elements.chatList || null,
    }

    function normalizeChat(raw = {}) {
      const chatId = String(
        raw?.chat_id ||
        raw?.session_id ||
        raw?.id ||
        ""
      ).trim()

      return {
        ...raw,
        chat_id: chatId,
        session_id: chatId,
        id: chatId,
        title: String(
          raw?.title ||
          raw?.name ||
          "New chat"
        ),
        created_at:
          raw?.created_at ||
          raw?.created ||
          "",
        updated_at:
          raw?.updated_at ||
          raw?.updated ||
          raw?.created_at ||
          raw?.created ||
          "",
      }
    }

    function normalizeChats(payload) {
      const list =
        Array.isArray(payload)
          ? payload
          : Array.isArray(payload?.sessions)
            ? payload.sessions
            : Array.isArray(payload?.chats)
              ? payload.chats
              : Array.isArray(payload?.items)
                ? payload.items
                : []

      return list
        .map(normalizeChat)
        .filter(
          (chat) =>
            String(
              chat?.chat_id ||
              chat?.session_id ||
              ""
            ).trim()
        )
    }

    function normalizeMessages(payload) {
      const list =
        Array.isArray(payload)
          ? payload
          : Array.isArray(payload?.messages)
            ? payload.messages
            : Array.isArray(payload?.items)
              ? payload.items
              : Array.isArray(payload?.turns)
                ? payload.turns
                : []

      return list.map((message) => ({
        ...message,
        message_id: String(
          message?.message_id ||
          message?.id ||
          ""
        ).trim(),
        id: String(
          message?.message_id ||
          message?.id ||
          ""
        ).trim(),
        role: String(
          message?.role ||
          "assistant"
        ),
        content: String(
          message?.content ||
          message?.text ||
          ""
        ),
        attachments: Array.isArray(
          message?.attachments
        )
          ? message.attachments
          : [],
      }))
    }

    function sortChatsNewestFirst(chats) {
      return [...chats].sort((a, b) => {
        const aTime =
          new Date(
            a?.updated_at ||
            a?.created_at ||
            0
          ).getTime() || 0

        const bTime =
          new Date(
            b?.updated_at ||
            b?.created_at ||
            0
          ).getTime() || 0

        return bTime - aTime
      })
    }

    async function listChats() {
      if (typeof apiClient.getState !== "function") {
        throw new Error(
          "NovaChatService: api.getState is required"
        )
      }

      const payload = await apiClient.getState()

      const chats = sortChatsNewestFirst(
        normalizeChats(payload)
      )

      state.chats = chats

      const serverActiveId = String(
        payload?.active_session_id ||
        payload?.activeSessionId ||
        payload?.session_id ||
        payload?.sessionId ||
        ""
      ).trim()

      if (serverActiveId) {
        state.activeChatId = serverActiveId
        state.chatId = serverActiveId
      }

      if (
        !state.activeChatId &&
        chats.length > 0
      ) {
        const firstId = String(
          chats[0]?.chat_id ||
          chats[0]?.session_id ||
          ""
        ).trim()

        if (firstId) {
          state.activeChatId = firstId
          state.chatId = firstId
        }
      }

      return chats
    }

    async function getMessages(chatId) {
      const id = String(
        chatId ||
        state.activeChatId ||
        state.chatId ||
        ""
      ).trim()

      if (!id) {
        state.messages = []
        return []
      }

      let payload

      if (typeof apiClient.getChat === "function") {
        payload = await apiClient.getChat(id)
      } else {
        throw new Error(
          "NovaChatService: api.getChat is required"
        )
      }

      const messages = normalizeMessages(
        payload
      )

      state.activeChatId = id
      state.chatId = id
      state.messages = messages

      if (
        state.messagesByChatId &&
        typeof state.messagesByChatId === "object"
      ) {
        state.messagesByChatId[id] = messages
      }

      return messages
    }

    async function loadChat(chatId) {
      const id = String(
        chatId || ""
      ).trim()

      if (!id) {
        state.messages = []
        return []
      }

      return await getMessages(id)
    }

    async function createChat() {
      if (
        typeof apiClient.createSession !==
        "function"
      ) {
        throw new Error(
          "NovaChatService: api.createSession is required"
        )
      }

      const payload =
        await apiClient.createSession({
          title: "New Chat",
        })

      const created = normalizeChat(
        payload?.chat ||
        payload?.session ||
        payload?.item ||
        payload ||
        {}
      )

      const createdId = String(
        created?.chat_id ||
        created?.session_id ||
        created?.id ||
        ""
      ).trim()

      if (createdId) {
        state.activeChatId = createdId
        state.chatId = createdId
        state.messages = []

        if (
          state.messagesByChatId &&
          typeof state.messagesByChatId === "object"
        ) {
          state.messagesByChatId[createdId] = []
        }
      }

      await listChats()

      if (createdId) {
        const matchingChat =
          Array.isArray(state.chats)
            ? state.chats.find(
                (chat) =>
                  String(
                    chat?.chat_id ||
                    chat?.session_id ||
                    ""
                  ) === createdId
              )
            : null

        if (matchingChat) {
          return matchingChat
        }
      }

      return created
    }

    async function renameChat(
      chatId,
      title
    ) {
      const id = String(
        chatId || ""
      ).trim()

      const nextTitle = String(
        title || ""
      ).trim()

      if (!id) {
        throw new Error(
          "NovaChatService.renameChat: chatId is required"
        )
      }

      if (!nextTitle) {
        throw new Error(
          "NovaChatService.renameChat: title is required"
        )
      }

      if (
        typeof apiClient.renameSession !==
        "function"
      ) {
        throw new Error(
          "NovaChatService: api.renameSession is required"
        )
      }

      const payload =
        await apiClient.renameSession(
          id,
          nextTitle
        )

      if (Array.isArray(state.chats)) {
        const target =
          state.chats.find(
            (chat) =>
              String(
                chat?.chat_id ||
                chat?.session_id ||
                ""
              ) === id
          )

        if (target) {
          target.title = nextTitle
          target.updated_at =
            new Date().toISOString()
        }

        state.chats =
          sortChatsNewestFirst(
            state.chats
          )
      }

      return payload
    }

    async function deleteChat(chatId) {
      const id = String(
        chatId || ""
      ).trim()

      if (!id) {
        throw new Error(
          "NovaChatService.deleteChat: chatId is required"
        )
      }

      if (
        typeof apiClient.deleteSession !==
        "function"
      ) {
        throw new Error(
          "NovaChatService: api.deleteSession is required"
        )
      }

      const payload =
        await apiClient.deleteSession(id)

      if (Array.isArray(state.chats)) {
        state.chats =
          state.chats.filter(
            (chat) =>
              String(
                chat?.chat_id ||
                chat?.session_id ||
                ""
              ) !== id
          )
      }

      if (
        String(
          state.activeChatId || ""
        ) === id ||
        String(
          state.chatId || ""
        ) === id
      ) {
        state.activeChatId = ""
        state.chatId = ""
        state.messages = []
      }

      if (
        state.messagesByChatId &&
        typeof state.messagesByChatId === "object"
      ) {
        delete state.messagesByChatId[id]
      }

      return payload
    }

    return {
      listChats,
      getMessages,
      loadChat,
      createChat,
      renameChat,
      deleteChat,
    }
  }

  window.NovaChatService = {
    create: createChatService,
    createChatService,
  }
})()