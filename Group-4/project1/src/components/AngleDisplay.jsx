import React from 'react';
import '../css/AngleDisplay.css';

function AngleDisplay({ angles, title }) {
  return (
    <div className="angles-panel">
      <h3>{title}</h3>
      <pre className="angles-json">{JSON.stringify(angles, null, 2)}</pre>
    </div>
  );
}

export default AngleDisplay;
