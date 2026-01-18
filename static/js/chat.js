const chatBody = document.getElementById('chat-body');
const chatFooter = document.getElementById('chat-footer');

let formData = {
    type: '',
    item_name: '',
    category: '',
    date_lost: '',
    location: '',
    description: '',
    image: null
};

const locations = {
    'A Block': ['1st Floor', '2nd Floor', '3rd Floor', '4th Floor'],
    'B Block': ['1st Floor', '2nd Floor'],
    'C Block': ['1st Floor', '2nd Floor', '3rd Floor'],
    'CC Hall': [],
    'Canteen': ['Aryas', 'VVDN']
};

function appendMessage(sender, text) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${sender === 'bot' ? 'bot-msg' : 'user-msg'}`;
    msgDiv.innerText = text;
    chatBody.appendChild(msgDiv);
    chatBody.scrollTop = chatBody.scrollHeight;
}

function showOptions(options, callback) {
    chatFooter.innerHTML = '';
    const container = document.createElement('div');
    container.className = 'options-container';

    options.forEach(opt => {
        const btn = document.createElement('button');
        btn.className = 'option-btn';
        btn.innerText = opt;
        btn.onclick = () => {
            appendMessage('user', opt);
            callback(opt);
        };
        container.appendChild(btn);
    });
    chatFooter.appendChild(container);
}

function showInput(type, callback, placeholder = '') {
    chatFooter.innerHTML = '';

    if (type === 'file') {
        const container = document.createElement('div');
        container.className = 'sketch-upload-container';
        container.innerHTML = `
            <div class="sketch-icon-circle">
                <div class="sketch-arrow"></div>
            </div>
            <div class="sketch-text">UPLOAD...</div>
            <input type="file" id="file-input" accept="image/*" style="display: none;">
        `;

        const fileInput = container.querySelector('#file-input');

        container.onclick = () => fileInput.click();

        fileInput.onchange = () => {
            if (fileInput.files.length > 0) {
                container.classList.add('uploading-animation');
                container.querySelector('.sketch-text').innerText = 'UPLOADING...';

                setTimeout(() => {
                    appendMessage('user', 'Image uploaded: ' + fileInput.files[0].name);
                    container.innerHTML = `
                        <div class="upload-success-tick">✓</div>
                        <div class="sketch-text">DONE!</div>
                    `;
                    setTimeout(() => callback(fileInput.files[0]), 1000);
                }, 1500);
            }
        };

        chatFooter.appendChild(container);
    } else {
        const input = document.createElement('input');
        input.type = type;
        input.placeholder = placeholder;
        input.required = true;

        const btn = document.createElement('button');
        btn.className = 'btn-signin';
        btn.innerText = 'Send';
        btn.style.marginTop = '0.5rem';

        btn.onclick = () => {
            if (input.value.trim() !== '') {
                appendMessage('user', input.value);
                callback(input.value);
            }
        };

        chatFooter.appendChild(input);
        chatFooter.appendChild(btn);
    }
}

// --- Flow Steps ---

function startChat() {
    appendMessage('bot', 'Welcome back! How can I help you today?');
    showOptions(['Report Lost Item', 'Report Found Item'], (choice) => {
        formData.type = choice.includes('Lost') ? 'LOST' : 'FOUND';
        askItemName();
    });
}

function askItemName() {
    appendMessage('bot', 'What is the name of the item?');
    showInput('text', (val) => {
        formData.item_name = val;
        askCategory();
    }, 'e.g. Blue Backpack');
}

function askCategory() {
    const cats = ['Bag', 'Wallet', 'ID Card', 'Mobile Phone', 'Earbuds', 'Laptop', 'Book', 'Personal Accessories'];
    appendMessage('bot', 'Please select a category:');
    showOptions(cats, (val) => {
        if (val === 'Personal Accessories') {
            appendMessage('bot', 'What exactly is it?');
            showInput('text', (subVal) => {
                formData.category = `Personal Acc: ${subVal}`;
                askImage();
            });
        } else {
            formData.category = val;
            askImage();
        }
    });
}

function askImage() {
    appendMessage('bot', 'Please upload a clear image of the item (Mandatory):');
    showInput('file', (file) => {
        formData.image = file;
        askDate();
    });
}

function askDate() {
    appendMessage('bot', formData.type === 'LOST' ? 'When did you lose it?' : 'When did you find it?');
    showInput('date', (val) => {
        formData.date_lost = val;
        askLocation();
    });
}

function askLocation() {
    appendMessage('bot', 'Which block?');
    showOptions(Object.keys(locations), (block) => {
        const floors = locations[block];
        if (floors.length > 0) {
            appendMessage('bot', 'Which section/floor?');
            showOptions(floors, (floor) => {
                formData.location = `${block} -> ${floor}`;
                askDescription();
            });
        } else {
            formData.location = block;
            askDescription();
        }
    });
}

function askDescription() {
    appendMessage('bot', 'Provide a short description (min 10 characters):');
    showInput('text', (val) => {
        if (val.length < 10) {
            appendMessage('bot', 'Description too short! Try again.');
            askDescription();
            return;
        }
        formData.description = val;
        submitReport();
    }, 'e.g. It has a key chain with a star...');
}

function submitReport() {
    chatFooter.innerHTML = 'Sending...';
    const body = new FormData();
    for (let key in formData) {
        body.append(key, formData[key]);
    }

    fetch('/report', {
        method: 'POST',
        body: body
    }).then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                appendMessage('bot', 'Thank you! Your report has been submitted. Status: PENDING.');
                appendMessage('bot', 'If a match is found, your status will update automatically in "My Reports".');
                chatFooter.innerHTML = '<a href="/my_reports" class="option-btn">View My Reports</a>';
            } else {
                appendMessage('bot', 'Error: ' + data.message);
            }
        });
}

startChat();
