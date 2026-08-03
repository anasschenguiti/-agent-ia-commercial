const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');

const FASTAPI_TEXT_URL = "http://localhost:8000/chat";
const FASTAPI_VOICE_URL = "http://localhost:8000/api/v1/voice/interact";

console.log("🚀 Démarrage du pont WhatsApp Web.js (Patch LID v3)...");

const client = new Client({
    authStrategy: new LocalAuth({ dataPath: "./.wwebjs_auth" }),
    puppeteer: {
        headless: true,
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--no-first-run',
            '--no-zygote',
            '--disable-gpu'
        ]
    }
});

client.on('qr', (qr) => {
    console.log('\n📲 Scannez ce QR code avec WhatsApp :\n');
    qrcode.generate(qr, { small: true });
});

client.on('ready', () => {
    console.log('\n✅ Client WhatsApp connecté et opérationnel !');
    console.log('🤖 En attente de messages texte & notes vocales...\n');
});

client.on('disconnected', (reason) => {
    console.log('⚠️ Client déconnecté :', reason);
});

// Téléchargement robuste via Puppeteer en accédant directement au Store WhatsApp Web
async function downloadAudioViaStore(client, messageData) {
    const result = await client.pupPage.evaluate(async (msgRaw) => {
        try {
            // 1. Vérifier la structure du Store disponible
            let Msg = null;
            try { Msg = window.require('WAWebCollections').Msg; } catch(e) {}
            if (!Msg && window.Store) Msg = window.Store.Msg;

            // 2. Diagnostiquer le store
            const storeInfo = {
                hasMsg: !!Msg,
                modelsType: Msg ? typeof Msg.models : 'N/A',
                modelsLen: Msg && Msg.models ? Msg.models.length : 0,
                hasGetAll: Msg ? typeof Msg.getAll : 'N/A',
            };

            // 3. Chercher le message audio dans tous les modèles disponibles
            let targetMsg = null;
            if (Msg && Msg.models && Msg.models.length > 0) {
                for (let i = Msg.models.length - 1; i >= 0; i--) {
                    const m = Msg.models[i];
                    if (m && (m.type === 'ptt' || m.type === 'audio')) {
                        targetMsg = m;
                        storeInfo.foundType = m.type;
                        storeInfo.foundMediaStage = m.mediaData ? m.mediaData.mediaStage : 'no mediaData';
                        break;
                    }
                }
            }

            // 4. Si rien trouvé, retourner les infos de debug
            if (!targetMsg) {
                // Afficher les 5 derniers types de messages dans le store
                const lastTypes = Msg && Msg.models 
                    ? Msg.models.slice(-5).map(m => m ? m.type : 'null') 
                    : [];
                return { 
                    error: 'Aucun message PTT/audio dans Msg.models',
                    storeInfo,
                    lastTypes
                };
            }

            // 5. Déclencher le téléchargement
            try {
                await targetMsg.downloadMedia({ 
                    downloadEvenIfExpensive: true, 
                    rmrReason: 1, 
                    isUserInitiated: true 
                });
            } catch(e) {
                storeInfo.downloadErr = e.message;
            }

            storeInfo.mediaStageAfter = targetMsg.mediaData ? targetMsg.mediaData.mediaStage : 'N/A';

            // 6. Récupérer le Blob depuis le cache ou mediaObject
            let blob = null;

            // Tentative 1 : InMemoryMediaBlobCache
            try {
                const cache = window.require('WAWebMediaInMemoryBlobCache').InMemoryMediaBlobCache;
                if (targetMsg.mediaObject && targetMsg.mediaObject.filehash) {
                    blob = cache.get(targetMsg.mediaObject.filehash);
                    storeInfo.fromCache = !!blob;
                }
            } catch(e) { storeInfo.cacheErr = e.message; }

            // Tentative 2 : mediaBlob.forceToBlob()
            if (!blob && targetMsg.mediaObject && targetMsg.mediaObject.mediaBlob) {
                try { blob = targetMsg.mediaObject.mediaBlob.forceToBlob(); storeInfo.fromMediaBlob = true; } catch(e) {}
            }

            // Tentative 3 : mediaData.blob direct
            if (!blob && targetMsg.mediaData && targetMsg.mediaData.blob) {
                blob = targetMsg.mediaData.blob;
                storeInfo.fromMediaDataBlob = true;
            }

            if (!blob) {
                storeInfo.noBlob = true;
                return { error: 'Blob introuvable après téléchargement', storeInfo };
            }

            // 7. Convertir en base64
            const reader = new FileReader();
            return new Promise((resolve) => {
                reader.onloadend = () => {
                    resolve({
                        data: reader.result.split(',')[1],
                        mimetype: blob.type || targetMsg.mimetype || 'audio/ogg',
                        storeInfo
                    });
                };
                reader.readAsDataURL(blob);
            });
        } catch(e) {
            return { error: e.message, stack: e.stack };
        }
    }, messageData);

    return result;
}

// Écoute des messages entrants
client.on('message', async (message) => {
    if (message.from === 'status@broadcast' || message.isStatus) return;

    const sender = message.from;
    const sessionId = sender.replace(/[^a-zA-Z0-9_-]/g, "_");

    // 🎙️ NOTE VOCALE (PTT / Audio)
    if (message.hasMedia && (message.type === 'audio' || message.type === 'ptt')) {
        console.log(`\n🎙️ Note vocale reçue de [${sender}] (type: ${message.type})`);
        console.log(`   ID brut: ${message.id ? JSON.stringify(message.id) : 'undefined'}`);
        console.log(`   _data.id: ${message._data && message._data.id ? JSON.stringify(message._data.id) : 'N/A'}`);

        try {
            // Tentative 1 : downloadMedia() standard (patché)
            let media = null;
            try {
                media = await message.downloadMedia();
            } catch(e) {
                console.log(`⚠️ downloadMedia() erreur: ${e.message}`);
            }

            if (media && media.data) {
                console.log(`✅ Audio récupéré via downloadMedia() ! Taille: ${media.data.length} bytes`);
            } else {
                // Tentative 2 : Extraction via Store WhatsApp Web
                console.log(`⏳ Tentative extraction via Store WhatsApp Web...`);
                const storeResult = await downloadAudioViaStore(client, null);
                console.log(`🔍 Store résultat:`, JSON.stringify(storeResult, null, 2));

                if (storeResult && storeResult.data) {
                    media = new MessageMedia(storeResult.mimetype, storeResult.data, 'voice_input.ogg');
                    console.log(`✅ Audio récupéré via Store ! Taille: ${storeResult.data.length} bytes`);
                }
            }

            if (!media || !media.data) {
                console.error("❌ Impossible de récupérer l'audio.");
                await message.reply("Marhaba ! Je n'ai pas pu accéder à votre note vocale. Pouvez-vous écrire votre question ?");
                return;
            }

            const audioBuffer = Buffer.from(media.data, 'base64');
            const mimeType = media.mimetype || 'audio/ogg';
            const audioFile = new File([audioBuffer], 'voice_input.ogg', { type: mimeType });

            const formData = new FormData();
            formData.append('file', audioFile);
            formData.append('session_id', sessionId);

            const voiceRes = await fetch(FASTAPI_VOICE_URL, { method: 'POST', body: formData });

            if (voiceRes.ok) {
                const result = await voiceRes.json();
                const transcription = result.user_transcript || result.text || "";
                const replyText = result.agent_response || result.response || "";
                const audioBase64 = result.audio_base64;

                console.log(`🗣️ Transcription : "${transcription}"`);
                console.log(`🤖 Réponse IA    : "${replyText}"`);

                if (audioBase64) {
                    const replyAudio = new MessageMedia('audio/mp3', audioBase64, 'response.mp3');
                    await client.sendMessage(sender, replyAudio, { sendAudioAsVoice: true });
                }
                await message.reply(`🤖 *Agent IA IKSATECH* :\n${replyText}`);
            } else {
                const err = await voiceRes.text();
                console.error(`❌ Erreur FastAPI Voice (${voiceRes.status}) : ${err}`);
                await message.reply("Marhaba ! Erreur lors de l'analyse vocale.");
            }
        } catch (err) {
            console.error("💥 Erreur note vocale :", err.message);
            await message.reply("Marhaba ! Une erreur s'est produite lors de la lecture de votre note vocale.");
        }
        return;
    }

    // 💬 MESSAGE TEXTE
    const bodyText = message.body ? message.body.trim() : "";
    if (!bodyText) return;

    console.log(`📩 Texte de [${sender}] : "${bodyText}"`);

    try {
        const response = await fetch(FASTAPI_TEXT_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: bodyText, session_id: sessionId })
        });

        if (response.ok) {
            const data = await response.json();
            const replyMessage = data.response || "Marhaba ! Merci pour votre message.";
            console.log(`🤖 Réponse texte : "${replyMessage}"`);
            await message.reply(replyMessage);
        } else {
            console.error(`❌ Erreur FastAPI (${response.status}) : ${await response.text()}`);
            await message.reply("Marhaba ! Service temporairement indisponible.");
        }
    } catch (error) {
        console.error("❌ Erreur connexion FastAPI :", error.message);
        await message.reply("Marhaba ! Erreur de connexion.");
    }
});

client.initialize();
