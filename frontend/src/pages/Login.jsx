import Form from "../components/Form.jsx";


function Login() {
  return (
    <div>
      <Form route="/api/token/" method="login" />
    </div>
  );
}
export default Login;