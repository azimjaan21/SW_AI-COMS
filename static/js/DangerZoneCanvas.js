import React, { useEffect, useRef, useState } from "react";
import { Stage, Layer, Line, Text } from "react-konva";
import axios from "axios";

const API_BASE = "http://127.0.0.1:8000/api/danger-zones";

const DangerZoneCanvas = ({ camId, containerId, persons = [] }) => {
  const [polygons, setPolygons] = useState([]);
  const [currentPoints, setCurrentPoints] = useState([]);
  const [dimensions, setDimensions] = useState({ width: 700, height: 480 });
  const [drawingMode, setDrawingMode] = useState(false);
  const [showControls, setShowControls] = useState(false);
  const stageRef = useRef();

  const [alert, setAlert] = useState(false);

  // Resize stage
  useEffect(() => {
    const updateSize = () => {
      const container = document.getElementById(containerId);
      if (container) {
        const { width, height } = container.getBoundingClientRect();
        setDimensions({ width, height });
      }
    };
    updateSize();
    window.addEventListener("resize", updateSize);
    return () => window.removeEventListener("resize", updateSize);
  }, [containerId]);

  // Load polygons from backend
  useEffect(() => {
    axios.get(`${API_BASE}/?camera_id=${camId}`).then((res) => {
      const formatted = res.data.map((zone) => zone.points);
      setPolygons(formatted);
    });
  }, [camId]);

  // Danger Zone Alert Check
  useEffect(() => {
    if (polygons.length === 0 || persons.length === 0) {
      setAlert(false);
      return;
    }

    const inZone = persons.some((kpArray) =>
      polygons.some((zone) => {
        const poly = zone.map(([x, y]) => [x * dimensions.width, y * dimensions.height]);
        return kpArray.some(([x, y, conf]) => conf > 0.5 && pointInPolygon([x, y], poly));
      })
    );
    setAlert(inZone);
  }, [polygons, persons, dimensions]);

  const pointInPolygon = (point, vs) => {
    // ray-casting algorithm
    const [x, y] = point;
    let inside = false;
    for (let i = 0, j = vs.length - 1; i < vs.length; j = i++) {
      const xi = vs[i][0], yi = vs[i][1];
      const xj = vs[j][0], yj = vs[j][1];
      const intersect = ((yi > y) !== (yj > y)) &&
        (x < ((xj - xi) * (y - yi)) / (yj - yi) + xi);
      if (intersect) inside = !inside;
    }
    return inside;
  };

  const handleClick = (e) => {
    if (!drawingMode) return;
    const stage = stageRef.current.getStage();
    const pointer = stage.getPointerPosition();
    setCurrentPoints((prev) => [...prev, pointer.x, pointer.y]);
  };

  const savePolygon = async () => {
    if (currentPoints.length < 6) return alert("At least 3 points required");

    const reshapedPoints = [];
    for (let i = 0; i < currentPoints.length; i += 2) {
      reshapedPoints.push([currentPoints[i] / dimensions.width, currentPoints[i + 1] / dimensions.height]);
    }

    await axios.post(`${API_BASE}/`, { camera_id: camId, points: reshapedPoints });
    setPolygons([...polygons, reshapedPoints]);
    setCurrentPoints([]);
    setDrawingMode(false);
  };

  const deleteAll = async () => {
    await axios.delete(`${API_BASE}/delete_all/${camId}/`);
    setPolygons([]);
    setCurrentPoints([]);
    setDrawingMode(false);
    setAlert(false);
  };

  return (
    <div style={{ position: "relative", width: dimensions.width, height: dimensions.height + 60 }}>
      <Stage width={dimensions.width} height={dimensions.height} ref={stageRef} onClick={handleClick}>
        <Layer>
          {polygons.map((points, i) => (
            <Line
              key={i}
              points={points.flat().map((val, idx) => (idx % 2 === 0 ? val * dimensions.width : val * dimensions.height))}
              closed
              stroke="red"
              fill="rgba(255,0,0,0.4)"
              strokeWidth={2}
            />
          ))}
          {currentPoints.length >= 2 && (
            <Line
              points={currentPoints}
              stroke="red"
              strokeWidth={2}
              fill="rgba(255,0,0,0.4)"
              closed
              dash={[10, 5]}
            />
          )}

          {/* Danger Zone Alert Banner */}
          {alert && (
            <Text
              text="⚠ Worker in Danger Zone"
              x={dimensions.width - 300}
              y={10}
              fontSize={22}
              fontStyle="bold"
              fill="red"
            />
          )}
        </Layer>
      </Stage>

      {/* Controls */}
      {!showControls && (
        <div style={{ position: "absolute", top: dimensions.height, width: "100%", display: "flex", justifyContent: "center" }}>
          <button onClick={() => setShowControls(true)}>Draw Danger Zone</button>
        </div>
      )}
      {showControls && (
        <div style={{ position: "absolute", top: dimensions.height, width: "100%", display: "flex", justifyContent: "flex-end", gap: "8px" }}>
          <button onClick={() => { setDrawingMode(!drawingMode); if(drawingMode) setCurrentPoints([]); }}>
            {drawingMode ? "Cancel Drawing" : "Add Polygon"}
          </button>
          {drawingMode && <button onClick={savePolygon} disabled={!currentPoints.length}>Save</button>}
          {!drawingMode && <>
            <button onClick={deleteAll}>Delete All</button>
            <button onClick={() => { setShowControls(false); setDrawingMode(false); setCurrentPoints([]); }}>Close Controls</button>
          </>}
        </div>
      )}
    </div>
  );
};

export default DangerZoneCanvas;
