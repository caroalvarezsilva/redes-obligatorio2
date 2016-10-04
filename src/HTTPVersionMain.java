import javax.swing.*;
import java.awt.*;
import java.awt.event.*;

/**
 * Created by caralvarez on 4/10/16.
 */
public class HTTPVersionMain extends JFrame {

    private JFrame mainFrame;
    private JLabel headerLabel;
    private JLabel statusLabel;
    private JPanel controlPanel;
    private HttpChecker httpChecker;

    public HTTPVersionMain() {
        prepareGUI();
    }

    public static void main(String[] args){
        HTTPVersionMain HTTPVersionMain = new HTTPVersionMain();
        HTTPVersionMain.showInterface();
    }

    private void prepareGUI(){
        mainFrame = new JFrame("Java Swing Examples");
        mainFrame.setSize(400,400);
        mainFrame.setLayout(new GridLayout(3, 1));
        mainFrame.addWindowListener(new WindowAdapter() {
            public void windowClosing(WindowEvent windowEvent){
                System.exit(0);
            }
        });
        headerLabel = new JLabel("", JLabel.CENTER);
        statusLabel = new JLabel("",JLabel.CENTER);

        statusLabel.setSize(350,100);

        controlPanel = new JPanel();
        controlPanel.setLayout(new FlowLayout());

        mainFrame.add(headerLabel);
        mainFrame.add(controlPanel);
        mainFrame.add(statusLabel);
        mainFrame.setVisible(true);

        httpChecker = new HttpChecker();
    }

    private void showInterface(){
        headerLabel.setText("Verify HTTP version");

        JLabel  namelabel= new JLabel("URL: ", JLabel.RIGHT);

        final JTextField urlText = new JTextField(20);
        JButton testButton = new JButton("Test");
        testButton.addActionListener(new ActionListener() {
            public void actionPerformed(ActionEvent e) {

                String data = urlText.getText();

                statusLabel.setText("<html>"+httpChecker.checkHttpVersion(urlText.getText())+"</html>");
                urlText.setText("");
            }
        });

        controlPanel.add(namelabel);
        controlPanel.add(urlText);
        controlPanel.add(testButton);
        mainFrame.setVisible(true);
    }
}
