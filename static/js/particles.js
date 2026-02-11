// Particle Background Logic
const canvas = document.getElementById('bg-canvas');
if (canvas) {
    const ctx = canvas.getContext('2d');
    let width, height;

    function resize() {
        width = window.innerWidth;
        height = window.innerHeight;
        canvas.width = width;
        canvas.height = height;
    }

    window.addEventListener('resize', resize);
    resize();

    // Fixed position to cover viewport
    canvas.style.position = 'fixed';
    canvas.style.top = '0';
    canvas.style.left = '0';
    canvas.style.zIndex = '0'; // Behind content
    canvas.style.pointerEvents = 'none';

    const particles = [];
    const particleCount = 350; // High density

    class Particle {
        constructor() {
            this.reset();
            this.y = Math.random() * height; // Scatter
        }

        reset() {
            this.x = Math.random() * width;
            this.y = Math.random() * height;
            this.vx = (Math.random() - 0.5) * 0.5;
            this.vy = (Math.random() - 0.5) * 0.5;
            this.size = Math.random() * 3 + 0.5;
            this.alpha = Math.random() * 0.8 + 0.2;
            this.fade = (Math.random() * 0.02) + 0.005;
        }

        update() {
            this.x += this.vx;
            this.y += this.vy;

            this.alpha -= this.fade;
            if (this.alpha <= 0.1 || this.alpha >= 1) {
                this.fade = -this.fade;
            }

            if (this.x < 0) this.x = width;
            if (this.x > width) this.x = 0;
            if (this.y < 0) this.y = height;
            if (this.y > height) this.y = 0;
        }

        draw() {
            ctx.fillStyle = `rgba(165, 180, 252, ${this.alpha})`;
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
            ctx.fill();
        }
    }

    // Init
    for (let i = 0; i < particleCount; i++) {
        particles.push(new Particle());
    }

    function animate() {
        ctx.clearRect(0, 0, width, height);
        particles.forEach(p => {
            p.update();
            p.draw();
        });
        requestAnimationFrame(animate);
    }
    animate();
}
