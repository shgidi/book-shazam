$(document).ready(function() {
    let likedBooks = [];

    // Use event delegation for dynamically added elements
    $(document).on('click', '#addBook', function() {
        const newInput = '<div class="book-input mb-4"><input type="text" class="liked-book shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline" placeholder="Enter a book title"></div>';
        $('#bookInputs').append(newInput);
    });

    $(document).on('click', '#submitBooks', function() {
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

    $(document).on('change', '#fileInput', function() {
        $('#fileName').text(this.files[0].name);
    });

    $(document).on('click', '#uploadButton', function() {
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

        $('#uploadButton').prop('disabled', true).html('<span class="loading mr-2"></span>Shazaming...');

        $.ajax({
            url: '/',
            type: 'POST',
            data: formData,
            contentType: false,
            processData: false,
            success: function(data) {
                $('#imageContainer').html('<img src="' + data.image + '" style="max-width: 100%;">');
                setupBookDetection(data.books);
                $('#uploadButton').prop('disabled', false).html('Shazam Books!');
            },
            error: function() {
                Swal.fire({
                    icon: 'error',
                    title: 'Oops...',
                    text: 'An error occurred while processing the image.',
                });
                $('#uploadButton').prop('disabled', false).html('Shazam Books!');
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
                    refineAndShowBookInfo(book, e.pageX, e.pageY);
                });
            });
        });

        $(document).click(function() {
            $('#contextMenu').hide();
        });
    }

    function refineAndShowBookInfo(book, x, y) {
        $('#contextMenu').html('<p class="text-sm">Refining book title...</p>').css({
            display: 'block',
            left: x + 'px',
            top: y + 'px'
        });

        $.ajax({
            url: '/refine_book_title',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ ocr_text: book.text }),
            success: function(data) {
                showBookInfo(data.refined_title, x, y);
            },
            error: function() {
                showBookInfo(book.text, x, y);
            }
        });
    }

    function showBookInfo(bookTitle, x, y) {
        $('#contextMenu').html(`
            <h3 class="font-semibold mb-2">${bookTitle}</h3>
            <button id="rateButton" class="bg-indigo-500 hover:bg-indigo-700 text-white font-bold py-1 px-2 rounded text-sm">
                Get Rating
            </button>
        `).css({
            display: 'block',
            left: x + 'px',
            top: y + 'px'
        });

        // Use event delegation for the rate button
        $(document).off('click', '#rateButton').on('click', '#rateButton', function() {
            getRating(bookTitle);
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
                showRecommendationModal(bookTitle, data.rating, data.reasoning);
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

    function showRecommendationModal(bookTitle, rating, reasoning) {
        $('#modal-title').text(`Book Shazam Rating for "${bookTitle}"`);
        $('#modal-rating').html(`<span class="text-2xl font-bold">${rating} out of 5 stars</span>`);
        $('#modal-reasoning').text(reasoning);
        $('#recommendationModal').removeClass('hidden');
    }

    $('#closeModal').click(function() {
        $('#recommendationModal').addClass('hidden');
    });

    // Close modal when clicking outside
    $(window).click(function(event) {
        if ($(event.target).is('#recommendationModal')) {
            $('#recommendationModal').addClass('hidden');
        }
    });

    // Recalculate highlight positions on window resize
    $(window).resize(function() {
        setupBookDetection(window.lastDetectedBooks || []);
    });
});