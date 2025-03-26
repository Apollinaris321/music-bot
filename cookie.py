import browser_cookie3

def export_youtube_cookies(output_file, browser):
    # Load cookies from the specified browser
    if browser.lower() == 'chrome':
        cookies = browser_cookie3.chrome()
    elif browser.lower() == 'firefox':
        cookies = browser_cookie3.firefox()
    elif browser.lower() == 'edge':
        cookies = browser_cookie3.edge()
    elif browser.lower() == 'safari':
        cookies = browser_cookie3.safari()
    else:
        print(f"Unsupported browser: {browser}")
        return

    # Filter cookies for youtube.com
    youtube_cookies = [cookie for cookie in cookies if "youtube.com" in cookie.domain]

    if youtube_cookies:
        # Write the cookies to the specified file in Netscape format
        with open(output_file, 'w') as file:
            file.write("# Netscape HTTP Cookie File\n")
            for cookie in youtube_cookies:
                file.write(f"{cookie.domain}\t")
                file.write("TRUE\t")
                file.write(f"{cookie.path}\t")
                file.write("FALSE\t")
                # Handle None expiration by using 0
                expires = int(cookie.expires) if cookie.expires else 0
                file.write(f"{expires}\t")
                file.write(f"{cookie.name}\t")
                file.write(f"{cookie.value}\n")
        print(f"All YouTube cookies exported to '{output_file}'")
    else:
        print("No YouTube cookies found.")


if __name__ == "__main__":
    # Hardcoded variables
    output_file = "cookies.txt"  # Replace with the desired output file name
    browser = "firefox"  # Replace with the browser you want to use (e.g., "chrome", "firefox", "edge", "safari")

    # Export YouTube cookies
    export_youtube_cookies(output_file, browser)