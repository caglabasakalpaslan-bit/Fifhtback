import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const interpretFeedback = async (text, song) => {
  const { data } = await axios.post(`${API}/interpret`, { text, song });
  return data;
};

export const confirmFeedback = async (payload) => {
  const { data } = await axios.post(`${API}/feedback/confirm`, payload);
  return data;
};

export const getPatterns = async () => {
  const { data } = await axios.get(`${API}/patterns`);
  return data;
};

export const askDistinction = async (payload) => {
  const { data } = await axios.post(`${API}/distinction`, payload);
  return data;
};

export const evaluateAnswer = async (payload) => {
  const { data } = await axios.post(`${API}/evaluate`, payload);
  return data;
};

export const getPatternRoom = async () => {
  const { data } = await axios.get(`${API}/pattern-room/analysis`);
  return data;
};

export const reanalyzePatternRoom = async () => {
  const { data } = await axios.post(`${API}/pattern-room/analyze`);
  return data;
};

export const addPatternRoomSignals = async (signals) => {
  const { data } = await axios.post(`${API}/pattern-room/add-signals`, { signals });
  return data;
};

export const getActionBoard = async () => {
  const { data } = await axios.get(`${API}/action-board`);
  return data;
};

export const createAction = async (payload) => {
  const { data } = await axios.post(`${API}/action-board`, payload);
  return data;
};

export const updateAction = async (id, payload) => {
  const { data } = await axios.patch(`${API}/action-board/${id}`, payload);
  return data;
};

// ---- The Fifth (prototype core) ----
export const getFifthStories = async () => {
  const { data } = await axios.get(`${API}/fifth/stories`);
  return data;
};

export const startFifth = async (payload) => {
  const { data } = await axios.post(`${API}/fifth/start`, payload, { timeout: 150000 });
  return data;
};

export const answerFifth = async (session_id, answer) => {
  const { data } = await axios.post(`${API}/fifth/answer`, { session_id, answer }, { timeout: 150000 });
  return data;
};

export const getFifthStatus = async () => {
  const { data } = await axios.get(`${API}/fifth/status`);
  return data;
};

export const getFifthSession = async (session_id) => {
  const { data } = await axios.get(`${API}/fifth/session/${session_id}`);
  return data;
};

// Translate backend failure states into one small object the UI can render honestly.
export const describeFifthError = (e) => {
  const status = e?.response?.status;
  const detail = e?.response?.data?.detail;
  if (status === 503 || detail === "model_unavailable") return { kind: "unavailable" };
  if (status === 502 || detail === "model_bad_output") return { kind: "bad_output" };
  if (status === 409) return { kind: "done", message: detail };
  if (status === 404) return { kind: "missing", message: detail };
  if (status === 400) return { kind: "invalid", message: detail };
  if (!e?.response) return { kind: "network" };
  return { kind: "unknown", message: detail };
};

// Four-role enrichment after a completed Reveal (LIBRARIAN → SKEPTIC → STORYTELLER). Slow; call after render.
export const enrichFifth = async (session_id) => {
  const { data } = await axios.post(`${API}/fifth/enrich/${session_id}`, {}, { timeout: 120000 });
  return data;
};

// Return loop: later, the user says what happened to a saved Fifth Card. No scoring, no profile.
export const returnCard = async (session_id, outcome, note) => {
  const { data } = await axios.post(`${API}/fifth/card/${session_id}/return`, { outcome, note: note || null });
  return data;
};
