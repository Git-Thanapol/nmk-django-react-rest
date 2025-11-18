import React from "react";
import api from "../api.js";
import Notes from "../components/Notes.jsx";
import "../styles/form.css";
import "../styles/home.css";
import "../styles/note.css";
import "../styles/loadingindicator.css";

function Home() {
  const [notes, setNotes] = React.useState([]);
  const [content, setContent] = React.useState("");
  const [title, setTitle] = React.useState("");

  React.useEffect(() => {
    getNote();
  }, []);

  const getNote = () => {
    api
      .get("/api/notes/").then((response) => {
        setNotes(response.data);
      })
      .catch((error) => {
        console.error("There was an error fetching the notes!", error);
      });
  }

  const deleteNote = (id) => {
    api
      .delete(`/api/notes/${id}/`).then((response) => {
        if (response.status === 204) alert("Note deleted successfully") 
        else alert("Failed to delete the note");
        getNote();
      }) 
      .catch((error) => {
        console.error("There was an error deleting the note!", error);
      });
  }

  const createNote = (e) => {
    e.preventDefault();
    api
      .post("/api/notes/", { title, content }).then((response) => {
        if (response.status === 201) alert("Note created successfully") 
        else alert("Failed to create the note");
        getNote();
      }).catch((error) => {
        console.error("There was an error creating the note!", error);
      })
      .finally(() => {
        setTitle("");
        setContent("");
        
      });
  }

  return (    
    <div>
      <h1>Welcome to the Home Page</h1>
      <div>
        <h1>Your Notes</h1>
        {notes.map((note) => (
          <Notes key={note.id} notes={note} onDelete={deleteNote} />
        ))}
      </div>

      <h2>Create a New Note</h2>
      <form onSubmit={createNote}>
        <label>Title:</label>
        <input id="Title" type="text" placeholder="Title" value={title} onChange={(e) => setTitle(e.target.value)} required />
        <br />
        <label>Content:</label>
        <textarea id="Content" placeholder="Content" value={content} onChange={(e) => setContent(e.target.value)} required />  
        <br />
        <button type="submit">Create Note</button>
      </form>
    </div>
  );
}

export default Home;