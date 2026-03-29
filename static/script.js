document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const uploadSection = document.querySelector('.upload-section');
    const resultSection = document.getElementById('result-section');
    const featuresSection = document.getElementById('features-section');
    const loadingSection = document.getElementById('loading');
    const resetBtn = document.getElementById('reset-btn');

    // Drag and Drop Events
    dropZone.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            handleFile(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files[0]) {
            handleFile(e.target.files[0]);
        }
    });

    // Reset Button
    resetBtn.addEventListener('click', () => {
        resultSection.classList.add('hidden');
        uploadSection.classList.remove('hidden');
        if (featuresSection) featuresSection.classList.remove('hidden');
        dropZone.classList.remove('hidden');
        loadingSection.classList.add('hidden');
        fileInput.value = '';
    });

    async function handleFile(file) {
        if (!file.type.startsWith('image/')) {
            alert('Please upload an image file.');
            return;
        }

        dropZone.classList.add('hidden');
        loadingSection.classList.remove('hidden');

        const formData = new FormData();
        formData.append('image', file);

        try {
            const response = await fetch('/api/analyze', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error('Analysis failed');
            }

            const data = await response.json();
            displayResults(data);
        } catch (error) {
            console.error('Error:', error);
            alert('Something went wrong during analysis. Please try again.');
            resetBtn.click();
        }
    }

    function displayResults(data) {
        uploadSection.classList.add('hidden');
        if (featuresSection) featuresSection.classList.add('hidden');
        resultSection.classList.remove('hidden');

        // Render Title
        document.getElementById('product-name').textContent = data.productName || 'Unknown Product';

        // Render Score
        const scoreCircle = document.getElementById('score-circle');
        const scoreText = document.getElementById('score-text');
        const score = data.score || 0;
        
        // Ensure animation triggers by a tiny timeout
        setTimeout(() => {
            // Circle circumference is approx 283
            const offset = 283 - (283 * score) / 100;
            scoreCircle.style.strokeDashoffset = offset;
            
            // Set Color based on score
            let color = 'var(--bad-color)';
            if (score >= 70) color = 'var(--good-color)';
            else if (score >= 40) color = 'var(--neutral-color)';
            
            scoreCircle.style.stroke = color;
            
            // Animate Number
            let current = 0;
            const step = Math.ceil(score / 30);
            const timer = setInterval(() => {
                current += step;
                if (current >= score) {
                    current = score;
                    clearInterval(timer);
                }
                scoreText.textContent = current;
                scoreText.style.color = color;
            }, 50);
        }, 100);

        // Render Ingredients
        const ingredientsList = document.getElementById('ingredients-list');
        ingredientsList.innerHTML = '';
        if (data.ingredients) {
            data.ingredients.forEach(ing => {
                const li = document.createElement('li');
                li.className = `item-card ${ing.status}`;
                li.innerHTML = `
                    <div class="item-header">
                        <span class="item-title">${ing.name}</span>
                        <span class="item-badge ${ing.status}-bg">${ing.status}</span>
                    </div>
                    <div class="item-desc">${ing.reason}</div>
                `;
                ingredientsList.appendChild(li);
            });
        }

        // Render Claims
        const claimsList = document.getElementById('claims-list');
        claimsList.innerHTML = '';
        if (data.claims && data.claims.length > 0) {
            data.claims.forEach(claim => {
                const isReal = claim.isReal;
                const statusClass = isReal ? 'true' : 'false';
                const label = isReal ? 'VERIFIED' : 'MISLEADING';
                
                const li = document.createElement('li');
                li.className = `item-card ${statusClass}`;
                li.innerHTML = `
                    <div class="item-header">
                        <span class="item-title">"${claim.claim}"</span>
                        <span class="item-badge ${statusClass}-bg">${label}</span>
                    </div>
                    <div class="item-desc">${claim.explanation}</div>
                `;
                claimsList.appendChild(li);
            });
        } else {
            claimsList.innerHTML = '<li class="item-card neutral"><div class="item-desc">No verifiable claims detected.</div></li>';
        }
    }
});
