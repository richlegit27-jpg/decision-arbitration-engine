(() => {
    "use strict";

    function getSessionId(button){
        const card =
            button?.closest(
                ".nova-tool-approval"
            )

        const cardSessionId =
            card?.dataset?.sessionId ||
            button?.dataset?.sessionId ||
            ""

        if(cardSessionId){
            return String(cardSessionId).trim()
        }

        const state =
            window.NovaChatState?.state ||
            window.Nova?.state ||
            {}

        return String(
            state.activeChatId ||
            state.active_chat_id ||
            state.session_id ||
            ""
        ).trim()
    }


    function setButtonsBusy(
        button,
        busy,
        text
    ){
        if(!button){
            return
        }

        const card =
            button.closest(
                ".nova-tool-approval"
            )

        const buttons =
            card?.querySelectorAll(
                "button"
            ) || []

        buttons.forEach((item) => {
            item.disabled = Boolean(busy)
        })

        if(text){
            button.textContent = text
        }
    }


    async function postApproval(
        endpoint,
        sessionId
    ){
        console.log(
            "[NOVA TOOL APPROVAL] sending",
            {
                endpoint,
                sessionId,
            }
        )

        const response = await fetch(
            endpoint,
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json",
                },

                body: JSON.stringify({
                    session_id: sessionId,
                }),
            }
        )

        let data = null

        try{
            data = await response.json()
        }catch(error){
            data = {
                ok: false,
                error: "Invalid server response.",
            }
        }

        if(!response.ok || !data?.ok){
            throw new Error(
                data?.error ||
                `Request failed (${response.status}).`
            )
        }

        return data
    }


    function updateApprovalCard(
        button,
        status,
        message
    ){
        const card =
            button?.closest(
                ".nova-tool-approval"
            )

        if(!card){
            return
        }

        const actions =
            card.querySelector(
                ".nova-tool-approval-actions"
            )

        if(actions){
            actions.innerHTML = `
                <div class="nova-tool-approval-result ${status}">
                    ${escapeHtml(message)}
                </div>
            `
        }
    }


    function escapeHtml(value){
        return String(value ?? "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;")
    }


    async function refreshState(){
        try{
            if(
                typeof window.NovaChatApp
                    ?.loadState === "function"
            ){
                await window.NovaChatApp.loadState()
            }

            window.dispatchEvent(
                new CustomEvent(
                    "nova:messages-changed"
                )
            )
        }catch(error){
            console.warn(
                "[NOVA TOOL APPROVAL] state refresh failed",
                error
            )
        }
    }


async function approve(
    messageId,
    button,
    approvalSessionId
){
    const sessionId =
        String(
            approvalSessionId ||
            getSessionId(button) ||
            ""
        ).trim()

    if(!sessionId){
        console.error(
            "[NOVA TOOL APPROVAL] missing session id"
        )

        alert(
            "Unable to determine the chat session for this tool approval."
        )

        return
    }

    const originalText =
        button?.textContent ||
        "Approve"

    try{
        setButtonsBusy(
            button,
            true,
            "Approving..."
        )

        const result =
            await postApproval(
                "/api/tools/approve",
                sessionId
            )

        console.log(
            "[NOVA TOOL APPROVAL] approved",
            {
                messageId,
                sessionId,
                result,
            }
        )

        updateApprovalCard(
            button,
            "approved",
            result?.formatted ||
            result?.message ||
            "Tool approved and executed."
        )

        await refreshState()

    }catch(error){
        console.error(
            "[NOVA TOOL APPROVAL] approve failed",
            {
                messageId,
                sessionId,
                error,
            }
        )

        setButtonsBusy(
            button,
            false,
            originalText
        )

        alert(
            error?.message ||
            "Unable to approve tool execution."
        )
    }
}

    async function deny(
        messageId,
        button,
        approvalSessionId
    ){
        const sessionId =
            String(
                approvalSessionId ||
                getSessionId(button) ||
                ""
            ).trim()

        if(!sessionId){
            console.error(
                "[NOVA TOOL APPROVAL] missing session id"
            )

            alert(
                "Unable to determine the chat session for this tool approval."
            )

            return
        }

        const originalText =
            button?.textContent ||
            "Deny"

        try{
            setButtonsBusy(
                button,
                true,
                "Cancelling..."
            )

            const result =
                await postApproval(
                    "/api/tools/deny",
                    sessionId
                )

            console.log(
                "[NOVA TOOL APPROVAL] denied",
                {
                    messageId,
                    sessionId,
                    result,
                }
            )

            updateApprovalCard(
                button,
                "denied",
                result?.message ||
                "Tool execution was cancelled."
            )

            await refreshState()

        }catch(error){
            console.error(
                "[NOVA TOOL APPROVAL] deny failed",
                {
                    messageId,
                    sessionId,
                    error,
                }
            )

            setButtonsBusy(
                button,
                false,
                originalText
            )

            alert(
                error?.message ||
                "Unable to deny tool execution."
            )
        }
    }


    window.NovaToolApprovalActions = {
        approve,
        deny,
    }


    console.log(
        "[NOVA TOOL APPROVAL ACTIONS] ready"
    )
})()