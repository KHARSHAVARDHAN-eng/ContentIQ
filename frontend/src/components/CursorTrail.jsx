import React, { useEffect, useRef } from 'react';

const CursorTrail = () => {
  const canvasRef = useRef(null);

  useEffect(() => {
    // Disable on mobile/tablet or coarse pointer devices
    const isMobile = window.matchMedia('(pointer: coarse)').matches || window.innerWidth < 768;
    if (isMobile) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    let animationFrameId;
    
    // Store cursor points
    let points = [];
    const maxAge = 120; // 2 seconds at ~60fps
    
    const resizeCanvas = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    // Track mouse coordinates
    const handleMouseMove = (e) => {
      points.push({
        x: e.clientX,
        y: e.clientY,
        age: 0
      });
    };
    window.addEventListener('mousemove', handleMouseMove);

    // Render loop
    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      
      if (points.length > 1) {
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';

        // Draw connecting segments with variable opacity
        for (let i = 1; i < points.length; i++) {
          const p1 = points[i - 1];
          const p2 = points[i];
          
          // Calculate opacity based on age (fade out older points)
          const opacity = 1 - p2.age / maxAge;
          if (opacity <= 0) continue;
          
          ctx.beginPath();
          // Draw with soft sky-blue color
          ctx.strokeStyle = `rgba(125, 211, 252, ${opacity * 0.45})`;
          ctx.shadowColor = `rgba(125, 211, 252, ${opacity * 0.25})`;
          ctx.shadowBlur = 4;
          
          // Thin elegant width that tapers at the tail
          ctx.lineWidth = 2.5 * opacity;
          
          ctx.moveTo(p1.x, p1.y);
          ctx.lineTo(p2.x, p2.y);
          ctx.stroke();
        }
      }

      // Age points and remove dead ones
      points = points
        .map(p => ({ ...p, age: p.age + 1 }))
        .filter(p => p.age < maxAge);

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener('resize', resizeCanvas);
      window.removeEventListener('mousemove', handleMouseMove);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 pointer-events-none z-40"
    />
  );
};

export default CursorTrail;
