const canvas = document.getElementById('inkCanvas');
const ctx = canvas.getContext('2d');
canvas.width = window.innerWidth;
canvas.height = window.innerHeight;

let lastX = 0;
let lastY = 0;

function draw(e) {
    ctx.beginPath();
    ctx.moveTo(lastX, lastY);
    ctx.lineTo(e.offsetX, e.offsetY);
    ctx.strokeStyle = '#333';
    ctx.lineWidth = 2;
    ctx.lineCap = 'round';
    ctx.stroke();

    lastX = e.offsetX;
    lastY = e.offsetY;
}

canvas.addEventListener('mousemove', draw);

// Scroll interaction
window.addEventListener('scroll', () => {
    const scrollPosition = window.scrollY;
    const content = document.querySelector('.content');
    content.style.opacity = Math.min(1, scrollPosition / 100);
});

// Click interaction
document.querySelector('.interactive-element').addEventListener('click', (e) => {
    const x = e.clientX;
    const y = e.clientY;
    ctx.beginPath();
    ctx.arc(x, y, 10, 0, Math.PI * 2);
    ctx.fillStyle = '#333';
    ctx.fill();
    ctx.closePath();
});

// Soundscapes
const audioContext = new (window.AudioContext || window.webkitAudioContext)();
const ambientSound = audioContext.createOscillator();
ambientSound.type = 'sine';
ambientSound.frequency.value = 440; // A4 note
ambientSound.connect(audioContext.destination);
ambientSound.start();

const clickSound = audioContext.createOscillator();
clickSound.type = 'sine';
clickSound.frequency.value = 880; // A5 note

document.querySelector('.interactive-element').addEventListener('click', () => {
    clickSound.connect(audioContext.destination);
    clickSound.start();
    setTimeout(() => {
        clickSound.disconnect();
    }, 100);
});