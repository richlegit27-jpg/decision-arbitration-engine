(() => {
    "use strict";

    function getComposerState() {
        window.Nova = window.Nova || {};

        const chatState = window.NovaChatState?.state;

        if (chatState) {
            window.Nova.state = chatState;

            if (!Array.isArray(chatState.messages)) {
                chatState.messages = [];
            }

            if (!Array.isArray(chatState.pendingAttachments)) {
                chatState.pendingAttachments = [];
            }

            if (typeof chatState.isStreaming !== "boolean") {
                chatState.isStreaming = false;
            }

            if (typeof chatState.isSending !== "boolean") {
                chatState.isSending = false;
            }

            return chatState;
        }

        if (!window.Nova.state) {
            window.Nova.state = {
                activeChatId: null,
                activeSessionId: null,
                chats: [],
                sessions: [],
                messages: [],
                messagesByChatId: {},
                models: [],
                selectedModel: null,
                pendingAttachments: [],
                attachedFiles: [],
                isLoadingChat: false,
                isAuthenticated: false,
                isStreaming: false,
                isSending: false,
                booted: false
            };
        }

        return window.Nova.state;
    }


    function createLiveComposerActions() {

        const composerFactory =
            window.NovaComposerActions?.createComposerActions ||
            window.NovaComposerActions?.create ||
            window.createComposerActions;


        if (typeof composerFactory !== "function") {

            console.warn(
                "[NovaComposer Bridge] waiting for createComposerActions",
                {
                    hasNovaComposerActions:
                        !!window.NovaComposerActions,

                    hasGlobalFactory:
                        typeof window.createComposerActions
                }
            );

            return false;
        }


        const streamService =
            window.NovaStreamService;


        if (
            !streamService ||
            typeof streamService.send !== "function"
        ) {
            console.warn(
                "[NovaComposer Bridge] waiting for NovaStreamService"
            );

            return false;
        }


        let inputController = null;
        let composerActionsInstance = null;


        if (
            window.NovaComposerInput &&
            typeof window.NovaComposerInput.create === "function"
        ) {

            inputController =
                window.NovaComposerInput.create({

                    elements: {
                        input:
                            document.getElementById("input")
                    },


                    onSubmit() {

                        if (
                            composerActionsInstance &&
                            typeof composerActionsInstance.sendCurrentMessage === "function"
                        ) {
                            composerActionsInstance.sendCurrentMessage();
                        }

                    },


                    onStateChange() {

                        if (
                            composerActionsInstance &&
                            typeof composerActionsInstance.updateComposerState === "function"
                        ) {
                            composerActionsInstance.updateComposerState();
                        }

                    }

                });


            if (
                inputController &&
                typeof inputController.bindEvents === "function"
            ) {
                inputController.bindEvents();
            }


            console.log(
                "[NovaComposer Bridge] input controller created"
            );

        } else {

            console.warn(
                "[NovaComposer Bridge] NovaComposerInput unavailable"
            );

        }



        composerActionsInstance =
            composerFactory({

                state:
                    getComposerState(),


                elements: {

                    sendBtn:
                        document.getElementById("sendBtn"),

                    stopBtn:
                        document.getElementById("stopBtn"),

                    attachBtn:
                        document.getElementById("attachBtn"),

                    messagesScroll:
                        document.getElementById("messages") ||
                        document.getElementById("chatMessages")

                },


                chatMessages:
                    window.NovaChatMessages || null,


                chatStorage:
                    window.NovaChatStorage || null,


                streamService:
                    streamService,


                inputController:
                    inputController,


                attachmentsController:
                    window.NovaAttachmentsService || null

            });



        if (!composerActionsInstance) {

            console.error(
                "[NovaComposer Bridge] failed to create ComposerActions instance"
            );

            return false;

        }



        window.NovaComposerActions =
            composerActionsInstance;



        window.NovaComposerBridge = {

            input:
                inputController,

            composerActions:
                composerActionsInstance

        };



        if (
            typeof composerActionsInstance.bindEvents === "function"
        ) {

            composerActionsInstance.bindEvents();

            console.log(
                "[NovaComposer Bridge] composer events bound"
            );

        }



        if (
            typeof composerActionsInstance.updateComposerState === "function"
        ) {

            composerActionsInstance.updateComposerState();

            console.log(
                "[NovaComposer Bridge] composer state synchronized"
            );

        }



        console.log(
            "[NovaComposerActions] live instance initialized",
            {
                hasSendCurrentMessage:
                    typeof composerActionsInstance.sendCurrentMessage === "function",

                hasStreamService:
                    !!window.NovaStreamService,

                hasStreamSend:
                    typeof window.NovaStreamService?.send === "function",

                hasInputController:
                    !!inputController
            }
        );


        return true;

    }



    function waitForComposerDependencies() {

        const started =
            Date.now();


        const timer =
            setInterval(() => {


                if (createLiveComposerActions()) {

                    clearInterval(timer);

                    console.log(
                        "[NovaComposer Bridge] dependencies ready"
                    );

                    return;
                }



                if (
                    Date.now() - started > 15000
                ) {

                    clearInterval(timer);

                    console.error(
                        "[NovaComposer Bridge] timed out waiting for composer dependencies"
                    );

                }


            }, 100);

    }



    waitForComposerDependencies();



    window.NovaComposer = {


        init(config = {}) {

            if (
                window.NovaComposerService?.init
            ) {

                return window.NovaComposerService.init(
                    config
                );

            }

            return null;

        },


        sendMessage(...args) {

            if (
                window.NovaComposerActions?.sendCurrentMessage
            ) {

                return window.NovaComposerActions.sendCurrentMessage(
                    ...args
                );

            }

            console.error(
                "[NovaComposer Bridge] sendCurrentMessage unavailable"
            );

            return null;

        },


        stopGenerating(...args) {

            if (
                window.NovaComposerActions?.stopGenerating
            ) {

                return window.NovaComposerActions.stopGenerating(
                    ...args
                );

            }

            return null;

        },


        updateComposerState(...args) {

            if (
                window.NovaComposerActions?.updateComposerState
            ) {

                return window.NovaComposerActions.updateComposerState(
                    ...args
                );

            }

            return null;

        },


        setPendingFiles(...args) {

            if (
                window.NovaComposerAttachments?.setPendingFiles
            ) {

                return window.NovaComposerAttachments.setPendingFiles(
                    ...args
                );

            }

            return null;

        }

    };


    console.log(
        "[NovaComposer Bridge] ready"
    );


})();