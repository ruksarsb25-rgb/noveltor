// In production VITE_API_BASE is the deployed backend URL.
// In dev it is empty, so all requests go through the Vite proxy (vite.config.js).
export const API_BASE = import.meta.env.VITE_API_BASE || "";
