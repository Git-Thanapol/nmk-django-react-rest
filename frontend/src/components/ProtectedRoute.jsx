import {Navigate} from 'react-router-dom';
import React, { useEffect, useState } from 'react';
import {jwtDecode} from "jwt-decode";
import { REFRESH_TOKEN, ACCESS_TOKEN } from '../constants.js';
import api from '../api.js';

function ProtectedRoute({children}) {
    const [isAuthenticated, setIsAuthenticated] = useState(null);

    const refreshTokenFn = async () => {
        const refreshTokenValue = localStorage.getItem(REFRESH_TOKEN);
        if (!refreshTokenValue) {
            setIsAuthenticated(false);
            return false;
        }

        try {
            const response = await api.post('/api/token/refresh/', {refresh: refreshTokenValue});
            if (response.status === 200) {
                const newAccessToken = response.data.access;
                localStorage.setItem(ACCESS_TOKEN, newAccessToken);
                return true;
            }
        } catch (error) {
            console.error("Failed to refresh token:", error);
            setIsAuthenticated(false);
        }
        return false;
    };

    const checkAuth = async () => {
        const token = localStorage.getItem(ACCESS_TOKEN);
        if (!token) {
            setIsAuthenticated(false);
            return;
        }

        try {
            const decodedToken = jwtDecode(token);
            const tokenExp = decodedToken.exp;
            const currentTime = Date.now() / 1000;

            if (tokenExp < currentTime) {
                const refreshed = await refreshTokenFn();
                setIsAuthenticated(refreshed);
            } else {
                setIsAuthenticated(true);
            }
        } catch (error) {
            console.error("Token decode error:", error);
            setIsAuthenticated(false);
        }
    };

    useEffect(() => {
        checkAuth();
    }, []);

    if (isAuthenticated === null) {
        return <div>Loading...</div>;
    }

    return isAuthenticated ? children : <Navigate to="/login" />;
}

export default ProtectedRoute;