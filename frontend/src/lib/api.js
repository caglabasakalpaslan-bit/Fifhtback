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
