import axios from "axios";
import { ACCESS_TOKEN, REFRESH_TOKEN } from "./constants.js";

const api = axios.create({
  baseURL:import.meta.env.VITE_API_BASE_URL
});

api.interceptors.request.use(
    (config) => {
        const accessToken = localStorage.getItem(ACCESS_TOKEN);
        if (accessToken) {
            config.headers.Authorization = `Bearer ${accessToken}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
)

export default api;