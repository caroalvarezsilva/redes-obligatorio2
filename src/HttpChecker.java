import java.net.*;
import java.io.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class HttpChecker {

    public String checkHttpVersion(String url) {
        try {
            String newLine = "<br/>";
            String response = "";
            String host = getDomainName(url);
            response += connectToHost(host, "1.0") + newLine;
            response += connectToHost(host, "1.1") + newLine;
            response += connectToHost(host, "2.0");
            System.out.println(response);
            return response;
        }catch (Exception e){
            return "An error has ocurred";
        }
    }

    private String connectToHost(String host, String protocol) {
        String result = "";
        try {
            Socket socket = new Socket(host, 80);

            PrintStream out = new PrintStream(socket.getOutputStream());
            BufferedReader in = new BufferedReader(new InputStreamReader(socket.getInputStream()));

            if(protocol.equalsIgnoreCase("1.0")){
                out.println("GET / HTTP/1.0");
            }else{
                out.println("GET / HTTP/1.1");
            }
            out.println("Host: " + host);

            if(protocol.equalsIgnoreCase("2.0")){
                out.println("Connection: Upgrade, HTTP2-Settings");
                out.println( "Upgrade: h2c");
                out.println( "HTTP2-Settings: <base64url encoding of HTTP/2 SETTINGS payload>");
            }
            out.println();
            out.flush();


            String line = in.readLine();
            System.out.println("RESPONSE :" + line);
            String httpResponse = getHttpVersionFromResponse(line);
            if(protocol.equalsIgnoreCase("1.0")){
                line = " supports " + protocol;
            }else if (protocol.equalsIgnoreCase("1.1")) {
                line = " supports " + httpResponse;

            }else if (protocol.equalsIgnoreCase("2.0")) {
                if(checkHTTP2(line)){
                    line = " supports HTTP 2.0";
                }else{
                    line = " doesn't support HTTP 2.0";
                }


            }


            result += host+  line;

            in.close();
            out.close();
            socket.close();
        } catch (Exception e) {
            e.printStackTrace();
        }
        return result;
    }

    private String getHttpVersionFromResponse(String line){
        String[] spaceSeparator = line.split(" ");
        String[] slashSeparator =  spaceSeparator[0].split("/");
        return slashSeparator[1];
    }

    private boolean checkHTTP2(String line){
        String[] spaceSeparator = line.split(" ");
        if (spaceSeparator[1].equalsIgnoreCase("101")){
            return true;
        }else{
            return false;
        }

    }
    public static String getDomainName(String url) throws URISyntaxException {
        if(url.startsWith("www.")){
            return url;

        }else{
            URI uri = new URI(url);
            String domain = uri.getHost();
            return domain.startsWith("www.") ? domain.substring(4) : domain;
        }

    }
}