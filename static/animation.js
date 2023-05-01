const canvas = document.getElementById('animationCanvas');
const ctx = canvas.getContext('2d');

canvas.width = window.innerWidth;
canvas.height = window.innerHeight;

const shapes = [];

class Shape {
    constructor(x, y, size, vx, vy) {
        this.x = x;
        this.y = y;
        this.size = size;
        this.vx = vx;
        this.vy = vy;
    }

    update() {
        this.x += this.vx;
        this.y += this.vy;

        // Reverse direction when the shape hits the edge of the screen
        if (this.x < 0 || this.x + this.size > canvas.width) {
            this.vx = -this.vx;
        }
        if (this.y < 0 || this.y + this.size > canvas.height) {
            this.vy = -this.vy;
        }
    }

    draw() {
        ctx.beginPath();
        ctx.rect(this.x, this.y, this.size, this.size);
        ctx.fillStyle = '#a69f8d';
        ctx.fill();
        ctx.closePath();
    }
}

function addShape() {
    const size = 3;
    const x = Math.random() * (canvas.width - size);
    const y = Math.random() * (canvas.height - size);
    const vx = Math.random() * 0.5 - 0.25;
    const vy = Math.random() * 0.5 - 0.25;
    shapes.push(new Shape(x, y, size, vx, vy));
}

function animate() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = 'black';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    shapes.forEach(shape => {
        shape.update();
        shape.draw();
    });

    requestAnimationFrame(animate);
}

// Add 100 shapes initially
for (let i = 0; i < 100; i++) {
    addShape();
}

animate();

// Add a new shape every 5 seconds
setInterval(addShape, 50);
