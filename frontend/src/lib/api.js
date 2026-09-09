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
  const { data } = await axios.post(`${API}/fifth/start`, payload, { timeout: 90000 });
  return data;
};

export const answerFifth = async (session_id, answer) => {
  const { data } = await axios.post(`${API}/fifth/answer`, { session_id, answer }, { timeout: 90000 });
  return data;
};
