import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const WaveGenerator = () => {
  const [waveType, setWaveType] = useState('sine');
  const [frequency, setFrequency] = useState(2);
  const [waveData, setWaveData] = useState([]);
  const [timeEnd, setTimeEnd] = useState(10);
  const [totalTime] = useState(50); // Total timeline length

  // Generate different wave types
  const generateWave = (type, freq, points = 2000) => {
    const data = [];
    for (let i = 0; i < points; i++) {
      const x = i / points * totalTime; // 0 to totalTime range
      let y = 0;
      
      switch(type) {
        case 'sine':
          y = Math.sin(2 * Math.PI * freq * x);
          break;
        case 'square':
          y = Math.sin(2 * Math.PI * freq * x) > 0 ? 1 : -1;
          break;
        case 'triangle':
          const phase = (freq * x) % 1;
          y = phase < 0.5 ? 4 * phase - 1 : -4 * phase + 3;
          break;
        case 'sawtooth':
          y = 2 * ((freq * x) % 1) - 1;
          break;
        default:
          y = Math.sin(2 * Math.PI * freq * x);
      }
      
      data.push({ x: x.toFixed(3), y: y.toFixed(3) });
    }
    return data;
  };

  useEffect(() => {
    setWaveData(generateWave(waveType, frequency));
  }, [waveType, frequency, totalTime]);

  // Filter data based on visible time range
  const visibleData = waveData.filter(d => {
    const x = parseFloat(d.x);
    return x <= timeEnd;
  });

  return (
    <div className="p-6 max-w-6xl mx-auto bg-gray-50 min-h-screen">
      <h1 className="text-3xl font-bold mb-6 text-gray-800">Wave Generator - Part 1</h1>
      
      <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4 text-gray-700">Basic Wave Types</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Wave Type
            </label>
            <select 
              value={waveType}
              onChange={(e) => setWaveType(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded-md"
            >
              <option value="sine">Sine Wave</option>
              <option value="square">Square Wave</option>
              <option value="triangle">Triangle Wave</option>
              <option value="sawtooth">Sawtooth Wave</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Frequency: {frequency}
            </label>
            <input 
              type="range"
              min="1"
              max="10"
              value={frequency}
              onChange={(e) => setFrequency(Number(e.target.value))}
              className="w-full"
            />
          </div>
        </div>

        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Time Window: 0 - {timeEnd.toFixed(1)} seconds
          </label>
          <input 
            type="range"
            min="1"
            max={totalTime}
            step="0.5"
            value={timeEnd}
            onChange={(e) => setTimeEnd(Number(e.target.value))}
            className="w-full"
          />
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>1s</span>
            <span>{totalTime}s</span>
          </div>
        </div>

        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={visibleData} margin={{ top: 5, right: 20, bottom: 20, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis 
              dataKey="x" 
              label={{ value: 'Time', position: 'insideBottom', offset: -5 }}
              domain={[0, timeEnd]}
              type="number"
              tickFormatter={(value) => Number(value).toFixed(1)}
            />
            <YAxis label={{ value: 'Amplitude', angle: -90, position: 'insideLeft' }} domain={[-1.5, 1.5]} />
            <Tooltip />
            <Line type="monotone" dataKey="y" stroke="#3b82f6" dot={false} strokeWidth={2} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="font-semibold text-blue-900 mb-2">📝 Part 1 Complete</h3>
        <p className="text-blue-800 text-sm">
          We've created basic wave generation with 4 types: sine, square, triangle, and sawtooth.
        </p>
        <p className="text-blue-800 text-sm mt-2">
          <strong>Next steps:</strong> Add noise, random intervals, and variable cycle lengths.
        </p>
      </div>
    </div>
  );
};

export default WaveGenerator;