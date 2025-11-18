import Form from "../components/Form.jsx";

function Register() {
  return (
    <div>
      <Form route="/api/user/register/" method="register" />
    </div>
  );
}  
export default Register;