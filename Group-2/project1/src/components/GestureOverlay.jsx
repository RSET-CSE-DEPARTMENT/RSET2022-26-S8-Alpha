import React from 'react';
import '../css/GestureOverlay.css';

function GestureOverlay({ gesture, confidence, show }) {
  if (!show) return null;
  
  return (
    <div className="gesture-overlay">
      <div className="gesture-name">{gesture}</div>
      <div className="gesture-confidence">{(confidence * 100).toFixed(0)}%</div>
    </div>
  );
}

export default GestureOverlay;
