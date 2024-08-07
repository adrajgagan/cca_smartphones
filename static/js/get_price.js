const backgrounds = [
    'url(/static/images/0.jpg)',
    'url(/static/images/1.jpg)',
    'url(/static/images/2.jpg)',
    'url(/static/images/3.jpg)',
];

let currentIndex = 0;

document.body.addEventListener('click', (event) => {
    // Check if the click is outside the container
    const container = document.querySelector('.container');
    if (!container.contains(event.target)) {
        currentIndex = (currentIndex + 1) % backgrounds.length;
        document.getElementById('background-overlay').style.backgroundImage = backgrounds[currentIndex];
    }
});
