import api from '../config/api';

export const quizService = {
  generateQuiz: async ({ documentId, numMcqs = 10, numShortQuestions = 5 }) => {
    const response = await api.post('/quiz/generate', {
      document_id: documentId,
      num_mcqs: numMcqs,
      num_short_questions: numShortQuestions,
    }, { timeout: 60000 });
    return response.data;
  },

  submitQuiz: async ({ answers, quizData, userId, documentId, documentName }) => {
    const payload = { answers, quiz_data: quizData };
    const parsedUserId = parseInt(userId, 10);
    if (!Number.isNaN(parsedUserId)) payload.user_id = parsedUserId;
    // documentId here is the UUID string from the in-memory store;
    // the submit endpoint accepts it as-is for topic inference only.
    if (documentId) payload.document_id = documentId;
    if (documentName) payload.document_name = documentName;
    const response = await api.post('/quiz/submit', payload);
    return response.data;
  },

  evaluateShortAnswer: async ({ studentAnswer, expectedAnswer }) => {
    const response = await api.post('/quiz/evaluate-short', {
      student_answer: studentAnswer,
      expected_answer: expectedAnswer,
    });
    return response.data;
  },
};
