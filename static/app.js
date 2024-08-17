$(document).ready(function() {
    let likedBooks = [];

    // File input change event
    $('#fileInput').change(function() {
        $('#fileName').text(this.files[0].name);
    });

    // Upload button click event
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

        $('#uploadButton').prop('disabled', true).html('<span class="loading mr-2"></span>Shazaming...');

        $.ajax({
            url: '/upload',
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

    // Add new book to liked books
    $('#addNewBook').click(function() {
        var newBook = $('#newBookInput').val().trim();
        if (newBook) {
            $.ajax({
                url: '/add_liked_book',
                type: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({ book_title: newBook }),
                success: function(response) {
                    if (response.success) {
                        $('#likedBooksList').append('<li>' + newBook + '</li>');
                        $('#newBookInput').val('');
                    } else {
                        Swal.fire({
                            icon: 'info',
                            title: 'Note',
                            text: response.message,
                        });
                    }
                },
                error: function() {
                    Swal.fire({
                        icon: 'error',
                        title: 'Oops...',
                        text: 'An error occurred while adding the book.',
                    });
                }
            });
        }
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

            container.css('position', 'relative');

            books.forEach((book, index) => {
                const [x1, y1, x2, y2] = book.bbox;
                const highlight = $('<div class="book-highlight"></div>').css({
                    left: x1 * scaleX,
                    top: y1 * scaleY,
                    width: (x2 - x1) * scaleX,
                    height: (y2 - y1) * scaleY,
                    position: 'absolute',
                    cursor: 'pointer'
                }).appendTo(container);

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
                liked_books: getLikedBooks()
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

    function getLikedBooks() {
        return $('#likedBooksList li').map(function() {
            return $(this).text();
        }).get();
    }

    function showRecommendationModal(bookTitle, rating, reasoning) {
        $('#bookTitle').text(bookTitle);
        $('#ratingText').text(`${rating} out of 5 stars`);
        $('#reasoningText').text(reasoning);
        
        // Generate star rating
        let starsHtml = '';
        for (let i = 1; i <= 5; i++) {
            if (i <= Math.floor(rating)) {
                starsHtml += '★';
            } else if (i - 0.5 <= rating) {
                starsHtml += '½';
            } else {
                starsHtml += '☆';
            }
        }
        $('#ratingStars').html(starsHtml);

        $('#recommendationModal').fadeIn(300);
    }

    $('#closeModal').click(function() {
        $('#recommendationModal').fadeOut(300);
    });

    // Close modal when clicking outside
    $(window).click(function(event) {
        if (event.target == document.getElementById('recommendationModal')) {
            $('#recommendationModal').fadeOut(300);
        }
    });

    // Recalculate highlight positions on window resize
    $(window).resize(function() {
        setupBookDetection(window.lastDetectedBooks || []);
    });
});