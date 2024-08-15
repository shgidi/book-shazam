$(document).ready(function() {
    let likedBooks = [];

    $('#addBook').click(function() {
        const newInput = '<div class="book-input mb-4"><input type="text" class="liked-book shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline" placeholder="Enter a book title"></div>';
        $('#bookInputs').append(newInput);
    });

    $('#submitBooks').click(function() {
        likedBooks = $('.liked-book').map(function() {
            return $(this).val().trim();
        }).get().filter(book => book !== '');

        if (likedBooks.length < 3) {
            Swal.fire({
                icon: 'error',
                title: 'Oops...',
                text: 'Please enter at least 3 books you\'ve enjoyed.',
            });
            return;
        }

        $('#bookForm').hide();
        $('#uploadForm').show();
    });

    $('#fileInput').change(function() {
        $('#fileName').text(this.files[0].name);
    });

    $('#uploadButton').click(function() {
        var file = $('#fileInput')[0].files[0];
        if (!file) {
            Swal.fire({
                icon: 'error',
                title: 'Oops...',
                text: 'Please select a file first.',
            });
            return;
        }

        var formData = new FormData();
        formData.append('file', file);

        $('#uploadButton').prop('disabled', true).html('<span class="loading mr-2"></span>Processing...');

        $.ajax({
            url: '/',
            type: 'POST',
            data: formData,
            contentType: false,
            processData: false,
            success: function(data) {
                $('#imageContainer').html('<img src="' + data.image + '" style="max-width: 100%;">');
                setupBookDetection(data.books);
                $('#uploadButton').prop('disabled', false).html('Upload and Detect');
            },
            error: function() {
                Swal.fire({
                    icon: 'error',
                    title: 'Oops...',
                    text: 'An error occurred while processing the image.',
                });
                $('#uploadButton').prop('disabled', false).html('Upload and Detect');
            }
        });
    });

    function setupBookDetection(books) {
        const img = $('#imageContainer img');
        const container = $('#imageContainer');

        // Remove any existing highlights
        $('.book-highlight').remove();

        // Wait for the image to load before setting up the highlights
        img.on('load', function() {
            const imgNaturalWidth = this.naturalWidth;
            const imgNaturalHeight = this.naturalHeight;
            const imgDisplayWidth = img.width();
            const imgDisplayHeight = img.height();

            const scaleX = imgDisplayWidth / imgNaturalWidth;
            const scaleY = imgDisplayHeight / imgNaturalHeight;

            const imgOffset = img.offset();

            books.forEach((book, index) => {
                const [x1, y1, x2, y2] = book.bbox;
                const highlight = $('<div class="book-highlight"></div>').css({
                    left: (x1 * scaleX) + imgOffset.left,
                    top: (y1 * scaleY) + imgOffset.top,
                    width: (x2 - x1) * scaleX,
                    height: (y2 - y1) * scaleY
                }).appendTo('body');

                highlight.on('click', function(e) {
                    e.stopPropagation();
                    showBookInfo(book, e.pageX, e.pageY);
                });
            });
        });

        $(document).click(function() {
            $('#contextMenu').hide();
        });
    }

    function showBookInfo(book, x, y) {
        $('#contextMenu').html(`
            <h3 class="font-semibold mb-2">${book.text}</h3>
            <button id="rateButton" class="bg-indigo-500 hover:bg-indigo-700 text-white font-bold py-1 px-2 rounded text-sm">
                Get Rating
            </button>
        `).css({
            display: 'block',
            left: x + 'px',
            top: y + 'px'
        });

        $('#rateButton').click(function() {
            getRating(book.text);
        });
    }

    function getRating(bookTitle) {
        $('#rateButton').prop('disabled', true).html('<span class="loading mr-2"></span>Rating...');

        $.ajax({
            url: '/rate_book',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                book_title: bookTitle,
                liked_books: likedBooks
            }),
            success: function(data) {
                Swal.fire({
                    icon: 'info',
                    title: `Rating for "${bookTitle}"`,
                    html: `<p class="text-xl font-bold mb-2">${data.rating} out of 5 stars</p><p>${data.reasoning}</p>`,
                });
                $('#rateButton').prop('disabled', false).html('Get Rating');
            },
            error: function() {
                Swal.fire({
                    icon: 'error',
                    title: 'Oops...',
                    text: 'Error getting book rating.',
                });
                $('#rateButton').prop('disabled', false).html('Get Rating');
            }
        });
    }

    // Recalculate highlight positions on window resize
    $(window).resize(function() {
        setupBookDetection(window.lastDetectedBooks || []);
    });
});