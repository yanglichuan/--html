package com.example.library.service;

import com.example.library.model.Book;
import com.example.library.repository.BookRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Optional;

@Service
public class BookService {

    @Autowired
    private BookRepository bookRepository;

    public List<Book> getAllBooks() {
        return bookRepository.findAll();
    }

    public Optional<Book> getBookById(Long id) {
        return bookRepository.findById(id);
    }

    @Transactional
    public Book addBook(Book book) {
        if (bookRepository.findByIsbn(book.getIsbn()).isPresent()) {
            throw new IllegalArgumentException("Book with this ISBN already exists");
        }
        if (book.getStatus() == null) {
            book.setStatus(Book.BookStatus.AVAILABLE);
        }
        return bookRepository.save(book);
    }

    @Transactional
    public Book updateBook(Long id, Book bookDetails) {
        Book book = bookRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("Book not found with id: " + id));

        book.setTitle(bookDetails.getTitle());
        book.setAuthor(bookDetails.getAuthor());
        book.setIsbn(bookDetails.getIsbn());
        book.setPublishDate(bookDetails.getPublishDate());
        
        return bookRepository.save(book);
    }

    @Transactional
    public void deleteBook(Long id) {
        if (!bookRepository.existsById(id)) {
            throw new IllegalArgumentException("Book not found with id: " + id);
        }
        bookRepository.deleteById(id);
    }

    @Transactional
    public Book borrowBook(Long id) {
        Book book = bookRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("Book not found with id: " + id));
        
        if (book.getStatus() != Book.BookStatus.AVAILABLE) {
            throw new IllegalStateException("Book is not available for borrowing");
        }
        
        book.setStatus(Book.BookStatus.BORROWED);
        return bookRepository.save(book);
    }

    @Transactional
    public Book returnBook(Long id) {
        Book book = bookRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("Book not found with id: " + id));

        if (book.getStatus() != Book.BookStatus.BORROWED) {
            throw new IllegalStateException("Book was not borrowed");
        }

        book.setStatus(Book.BookStatus.AVAILABLE);
        return bookRepository.save(book);
    }

    public List<Book> searchBooks(String keyword) {
        // Simple search implementation
        List<Book> byTitle = bookRepository.findByTitleContainingIgnoreCase(keyword);
        List<Book> byAuthor = bookRepository.findByAuthorContainingIgnoreCase(keyword);
        byTitle.addAll(byAuthor);
        return byTitle.stream().distinct().toList();
    }
}
