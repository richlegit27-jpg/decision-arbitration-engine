document.addEventListener("DOMContentLoaded", () => {
    const backendPort = window.NOVA_BACKEND_PORT;
    const voicePanel = document.getElementById("voicePanel");

    voicePanel.innerHTML = `
        <button id="startRecording">Start Recording</button>
        <button id="stopRecording" disabled>Stop Recording</button>
        <button id="playAI">Play AI TTS</button>
        <audio id="playback" controls style="display:block;margin-top:10px;"></audio>
    `;

    const startBtn = document.getElementById("startRecording");
    const stopBtn = document.getElementById("stopRecording");
    const playBtn = document.getElementById("playAI");
    const playback = document.getElementById("playback");

    let mediaRecorder;
    let audioChunks = [];

    // ----------------------------
    // Record user audio
    // ----------------------------
    startBtn.addEventListener("click", async () => {
        if(!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia){
            alert("Microphone not supported");
            return;
        }
        const stream = await navigator.mediaDevices.getUserMedia({audio:true});
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
        mediaRecorder.start();
        startBtn.disabled = true;
        stopBtn.disabled = false;
    });

    stopBtn.addEventListener("click", () => {
        if(mediaRecorder && mediaRecorder.state !== "inactive"){
            mediaRecorder.stop();
            mediaRecorder.onstop = () => {
                const blob = new Blob(audioChunks, {type:"audio/webm"});
                playback.src = URL.createObjectURL(blob);
                // Optional: auto add to attachments panel
                if(window.addAttachment){
                    const file = new File([blob], `voice_${Date.now()}.webm`, {type:"audio/webm"});
                    window.addAttachment(file);
                }
            };
        }
        startBtn.disabled = false;
        stopBtn.disabled = true;
    });

    // ----------------------------
    // Play AI TTS
    // ----------------------------
    playBtn.addEventListener("click", async () => {
        try {
            // Fetch latest AI message from chat memory
            const res = await fetch(`http://127.0.0.1:${backendPort}/api/chat/history`);
            const data = await res.json();
            const aiMsgs = data.filter(m => m.role==="assistant");
            if(aiMsgs.length === 0) return alert("No AI messages to play.");
            const lastMsg = aiMsgs[aiMsgs.length-1].content;

            // Use browser TTS
            const utterance = new SpeechSynthesisUtterance(lastMsg);
            utterance.lang = 'en-US';
            window.speechSynthesis.speak(utterance);
        } catch(err){
            alert("AI TTS playback failed.");
        }
    });
});