import { useState } from "react";
import api from "../api";
import { useNavigate } from "react-router-dom";
import { ACCESS_TOKEN, REFRESH_TOKEN } from "../constants";
import "../styles/Form.css";
import LoadingIndicator from "./LoadingIndicator";

function Form({route,method}){
    const [username,setUsername] = useState("");
    const [password,setPassword] = useState("");
    const [Loading,setLoading] = useState(false);
    const [error,setError] = useState(null);
    const navigate = useNavigate();

    const name= method ==="login" ? "Login" : "Register";

    const handleSubmit = async (e) => {        
        setLoading(true);
        setError(null);
        e.preventDefault();

        try {
            const response = await api({
                method: 'post',
                url: route,
                data: {
                    username,
                    password
                }
            });
            if (response.status === 200 || response.status === 201) {
                if (method === "login") {
                    localStorage.setItem(ACCESS_TOKEN, response.data.access);
                    localStorage.setItem(REFRESH_TOKEN, response.data.refresh);
                    navigate("/");
                } else{
                    //setLoading(false);
                    navigate("/login");
                }
            }
        }
        catch (err) {
            setError(err.response ? err.response.data.detail : "Network Error");
            alert(error)
            //setLoading(false);
        } finally {
            setLoading(false);
        }
    };

    return(
        <form onSubmit={handleSubmit} className="form-container">
            <h1>{name}</h1>
            <input
                className="form-input"
                type="text"
                placeholder="Username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
            />
            <input
                className="form-input"
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
            />
            {Loading && <LoadingIndicator />}
            <button type="submit" disabled={Loading} className="form-button">
                {Loading ? "Loading..." : name}
            </button>
            {error && <p className="error-message">{error}</p>}
        </form>
    )
}

export default Form;