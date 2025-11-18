import React from "react";

function Notes({ notes, onDelete }) {
    const formatDate = (dateString) => {
        const options = { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' };
        return new Date(dateString).toLocaleDateString(undefined, options);
    }

  return (
    <div className="note-container">
        <p className="note-title">{notes.title}</p>
        <p className="note-content">{notes.content}</p>
        <p className="note-date">Created at: {formatDate(notes.created_at)}</p>
        <button className="delete-button" onClick={() => onDelete(notes.id)}>Delete</button>
    </div>
    );
}

export default Notes;