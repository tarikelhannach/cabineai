// frontend/src/services/geminiService.js
// Google Gemini 2.0 Flash integration for Arabic legal chat

import { GoogleGenerativeAI } from "@google/generative-ai";

class GeminiChatService {
    constructor(apiKey) {
        if (!apiKey) {
            console.warn("Gemini API key not configured");
            this.enabled = false;
            return;
        }

        this.enabled = true;
        this.genAI = new GoogleGenerativeAI(apiKey);

        // Use Gemini 2.0 Flash for optimal Arabic support
        this.model = this.genAI.getGenerativeModel({
            model: "gemini-2.0-flash-exp",
            generationConfig: {
                temperature: 0.7,
                topP: 0.95,
                topK: 40,
                maxOutputTokens: 2048,
            },
            safetySettings: [
                {
                    category: "HARM_CATEGORY_HARASSMENT",
                    threshold: "BLOCK_MEDIUM_AND_ABOVE",
                },
                {
                    category: "HARM_CATEGORY_HATE_SPEECH",
                    threshold: "BLOCK_MEDIUM_AND_ABOVE",
                },
            ],
        });

        this.chat = null;
        this.conversationHistory = [];
    }

    isEnabled() {
        return this.enabled;
    }

    /**
     * Start a new chat session with system context
     * @param {string} systemPrompt - System instructions for the AI
     * @param {string} documentContext - Optional context from documents
     */
    async startChat(systemPrompt, documentContext = null) {
        if (!this.enabled) {
            throw new Error("Gemini service not enabled");
        }

        // Build conversation history
        const history = [
            {
                role: "user",
                parts: [{ text: systemPrompt }]
            },
            {
                role: "model",
                parts: [{ text: "أنا مساعد قانوني متخصص في القانون المغربي. كيف يمكنني مساعدتك؟" }]
            }
        ];

        // Add document context if provided
        if (documentContext) {
            history.push({
                role: "user",
                parts: [{ text: `السياق من المستندات:\n${documentContext}` }]
            });
            history.push({
                role: "model",
                parts: [{ text: "شكراً، لقد استوعبت السياق. كيف يمكنني مساعدتك بخصوص هذه المستندات؟" }]
            });
        }

        this.conversationHistory = history;
        this.chat = this.model.startChat({ history });
    }

    /**
     * Send a message with streaming response
     * @param {string} message - User message
     * @param {function} onChunk - Callback for each chunk of response
     * @returns {Promise<string>} - Full response text
     */
    async sendMessage(message, onChunk = null) {
        if (!this.enabled || !this.chat) {
            throw new Error("Chat not initialized");
        }

        try {
            const result = await this.chat.sendMessageStream(message);

            let fullText = "";
            for await (const chunk of result.stream) {
                const chunkText = chunk.text();
                fullText += chunkText;

                // Call chunk callback if provided
                if (onChunk && typeof onChunk === 'function') {
                    onChunk(chunkText);
                }
            }

            return fullText;
        } catch (error) {
            console.error("Gemini sendMessage error:", error);
            throw error;
        }
    }

    /**
     * Send a message without streaming (faster for simple queries)
     * @param {string} message - User message
     * @returns {Promise<string>} - Response text
     */
    async sendMessageSync(message) {
        if (!this.enabled || !this.chat) {
            throw new Error("Chat not initialized");
        }

        try {
            const result = await this.chat.sendMessage(message);
            return result.response.text();
        } catch (error) {
            console.error("Gemini sendMessageSync error:", error);
            throw error;
        }
    }

    /**
     * Analyze an image (e.g., scanned legal document)
     * @param {string} imageData - Base64 encoded image data
     * @param {string} mimeType - Image MIME type (e.g., 'image/jpeg')
     * @param {string} prompt - Analysis prompt
     * @returns {Promise<string>} - Analysis result
     */
    async analyzeImage(imageData, mimeType, prompt) {
        if (!this.enabled) {
            throw new Error("Gemini service not enabled");
        }

        try {
            const imagePart = {
                inlineData: {
                    data: imageData,
                    mimeType: mimeType
                }
            };

            const result = await this.model.generateContent([
                prompt,
                imagePart
            ]);

            return result.response.text();
        } catch (error) {
            console.error("Gemini analyzeImage error:", error);
            throw error;
        }
    }

    /**
     * Extract structured data from image
     * @param {string} imageData - Base64 encoded image
     * @param {string} mimeType - Image MIME type
     * @returns {Promise<object>} - Extracted data as JSON
     */
    async extractDataFromImage(imageData, mimeType) {
        const prompt = `حلل هذا المستند القانوني واستخرج المعلومات التالية بصيغة JSON:

{
  "document_type": "نوع المستند (عقد، حكم، فاتورة، إلخ)",
  "parties": ["قائمة الأطراف المعنية"],
  "dates": ["التواريخ المهمة بصيغة YYYY-MM-DD"],
  "amounts": [{"value": رقم, "currency": "العملة"}],
  "location": "الموقع أو المحكمة",
  "summary": "ملخص تنفيذي مختصر"
}

إذا لم تجد معلومة معينة، استخدم null.`;

        const result = await this.analyzeImage(imageData, mimeType, prompt);

        try {
            // Try to parse JSON from response
            const jsonMatch = result.match(/\{[\s\S]*\}/);
            if (jsonMatch) {
                return JSON.parse(jsonMatch[0]);
            }
            return { raw_text: result };
        } catch (error) {
            console.error("Failed to parse JSON from image analysis:", error);
            return { raw_text: result };
        }
    }

    /**
     * Get conversation history
     * @returns {Array} - Conversation history
     */
    getHistory() {
        return this.conversationHistory;
    }

    /**
     * Clear conversation and start fresh
     */
    reset() {
        this.chat = null;
        this.conversationHistory = [];
    }
}

// System prompts for different contexts
export const SYSTEM_PROMPTS = {
    general: `أنت مساعد قانوني متخصص في القانون المغربي والشريعة الإسلامية.

مهامك:
1. الإجابة على الأسئلة القانونية باللغة العربية
2. تحليل المستندات القانونية (عقود، أحكام، فواتير)
3. استخراج المعلومات الرئيسية (الأطراف، التواريخ، المبالغ)
4. تقديم المشورة القانونية الأولية

قواعد:
- استخدم اللغة العربية الفصحى
- كن دقيقاً ومهنياً
- اذكر المصادر القانونية عند الإمكان
- إذا لم تكن متأكداً، قل ذلك بوضوح
- احترم خصوصية المعلومات`,

    documentAnalysis: `أنت خبير في تحليل المستندات القانونية المغربية.

مهمتك:
- تحليل المستندات بدقة
- استخراج المعلومات المهمة
- تحديد نوع المستند
- تلخيص المحتوى

استخدم اللغة العربية دائماً.`,

    drafting: `أنت مساعد في صياغة المستندات القانونية المغربية.

مهمتك:
- مساعدة المستخدمين في صياغة العقود والوثائق
- اقتراح صيغ قانونية مناسبة
- التأكد من الامتثال للقانون المغربي

استخدم لغة قانونية دقيقة ومهنية.`
};

export default GeminiChatService;
