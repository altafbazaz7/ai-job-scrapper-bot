const express = require("express");
const { GoogleGenAI } = require("@google/genai");
const dotenv = require("dotenv");
dotenv.config();

const app = express();
app.use(express.json());

const ai = new GoogleGenAI({
  apiKey: process.env.GOOGLE_API_KEY
});

const SYSTEM_PROMPT = `
You are JD Analyzer AI, a smart assistant designed to evaluate job descriptions for Mohammad Altaf Bazaz.

Candidate summary:
- MERN Stack Developer (4+ years)
- Strong in React.js, Next.js, TypeScript, React Native (3/5 proficiency)
- Skilled with Node.js, Express.js, MongoDB, MySQL, PostgreSQL
- Familiar with AWS, Google Cloud, CI/CD
- Open to relocation
- Hands-on with automation, GenAI integration, and scalable full-stack apps

Instructions:
- Evaluate how well a job description matches this profile.
- Focus on required skills, technologies, years of experience, cloud/tools familiarity, relocation, and mobile app relevance.
- Return a match score between 1-10 (1 = no match, 10 = perfect match).
- Respond ONLY with the score number. No extra commentary.
`;

let chat = null;
const history = [];

async function askJDAnalyzer(message) {
  if (!chat) {
    chat = await ai.chats.create({
      model: "gemini-2.5-flash",
      history: history,
      config: {
        systemInstruction: SYSTEM_PROMPT
      }
    });
  }

  history.push({ role: "user", parts: [{ text: message }] });

  const response = await chat.sendMessage({ message });
  const text = response.text ?? "No response from Gemini.";

  history.push({ role: "model", parts: [{ text }] });

  return text;
}

app.post("/evaluate", async (req, res) => {
  const { job_text } = req.body;

  if (!job_text) {
    return res.status(400).json({ error: "Missing job_text" });
  }

  try {
    const reply = await askJDAnalyzer(job_text);
    res.json({ reply });
  } catch (err) {
    console.error("❌ Error:", err);
    res.status(500).json({ error: err.toString() });
  }
});

app.listen(3000, () => {
  console.log("🚀 JD Analyzer server running at http://localhost:3000");
});
